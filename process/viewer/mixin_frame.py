import logging
import time
from pathlib import Path

import torch

from configs.settings import GPU_AHEAD, RANDOM_JUMP_PREWARM
from process.perf.present import PRESENT_PERF, note_render
from process.camera import _viewmat_from_cam
from process.common import display_name
from process.data.buffer import FrameBuffer
from process.data.compose import compose_splats
from process.handle import overlay_event
from process.perf.collector import perf_push
import process.viewer.render as viewer_render

logger = logging.getLogger(__name__)

class FrameMixin:

    @property
    def _files(self) -> list[Path]:
        return self._inputs[self._active_id]['files']

    @property
    def _buf(self) -> FrameBuffer:
        return self._inputs[self._active_id]['buf']

    @property
    def _local_idx(self) -> int:
        return self._idx % max(1, len(self._files))

    def input_ids(self) -> list[str]:
        return list(self._inputs.keys())

    def set_active_seq_input(self, input_id: str | None) -> None:
        new_player = (
            self._seq_players.get(input_id) if input_id else None
        )
        if new_player is self._seq_player:
            return
        self._seq_player = new_player
        tgt = (
            f'Object({display_name(self, input_id)})'
            if input_id else 'Object'
        )
        overlay_event(logger, tgt, 'Update', attr='SeqOverlay',
                      value='on' if input_id else 'off', to_file=True)
        self._render_current()

    def set_active_input(self, name: str) -> None:
        if name not in self._inputs or name == self._active_id:
            return
        self._active_id = name
        overlay_event(logger, f'Object({display_name(self, name)})',
                      'Activate', to_file=True)
        self._render_current()

    def _render_current(self) -> None:
        if self._rendering:
            return
        self._rendering = True

        _pp_t0 = time.perf_counter() if PRESENT_PERF else 0.0
        try:
            viewer_render.render_current_impl(self)
            if PRESENT_PERF:
                note_render(self, (time.perf_counter() - _pp_t0) * 1000.0)
        except Exception:
            logger.exception('Render error')
            raise
        finally:
            self._rendering = False

    def set_frame(self, idx: int) -> None:

        if self._scheduler is not None:
            self._render_playlist_frame()
            return

        if self._play_order is not None:
            self._render_play_order_frame()
            return
        self._idx = idx % max(1, self._total_frames)

        if self._chain_segments:
            self._sync_chain_segment()

        mapped = bool(self._frame_index_mappers)
        active_local = self._idx

        _dbg = logger.isEnabledFor(logging.DEBUG)
        _tf = time.perf_counter() if _dbg else 0.0
        new_splats: dict = {}
        for iid, entry in self._inputs.items():
            count = max(1, len(entry['files']))
            base = self._idx % count
            local = base
            for mapper in self._frame_index_mappers:
                local = mapper(iid, local, count)
            local = max(0, min(count - 1, local))
            new_splats[iid] = entry['buf'].get(local)

            warm_src = self._frame_warm_source
            entry['buf'].warm(
                base if warm_src is None else warm_src(iid, base, local)
            )
            if iid == self._active_id:
                active_local = local

        follow = self._seq_overlay_follow_mapper
        self._seq_idx = active_local if (mapped and follow) else self._idx
        self._splats = new_splats
        self._splat = compose_splats(self._splats)
        if _dbg:
            perf_push(self, fetch=(time.perf_counter() - _tf) * 1000.0)
        self._render_current()
        logger.debug('Frame %d rendered', self._idx)

    def _advance_playlist(self, steps: int) -> None:

        sch = self._scheduler
        for _ in range(steps):
            if sch.stopped:
                break
            sch.tick()
        self._render_playlist_frame()

    def _render_playlist_frame(self) -> None:

        sch = self._scheduler
        iids = list(self._inputs.keys())
        iid = iids[sch.active()]
        entry = self._inputs[iid]
        count = max(1, len(entry['files']))
        local = max(0, min(count - 1, sch.local))
        if iid != self._active_id:

            prev_buf = self._inputs[self._active_id]['buf']
            _dbg = logger.isEnabledFor(logging.DEBUG)
            if _dbg:
                torch.cuda.synchronize()
                _tsw = time.perf_counter()
            prev_buf.set_gpu_ahead(0)
            prev_buf.release_gpu()
            entry['buf'].set_gpu_ahead(GPU_AHEAD)
            if _dbg:
                torch.cuda.synchronize()
                logger.debug(
                    'PERF playlist switch -> %s: release+restore %.2fms',
                    iid, (time.perf_counter() - _tsw) * 1000.0,
                )
            self._playlist_prefetched = False
            self._active_id = iid
            self.set_active_seq_input(iid)
            hook = self._playlist_switch_hook
            if hook is not None:
                hook(iid)

        fsync = self._playlist_frame_sync
        if fsync is not None:
            fsync(iid, local, count)

        if not self._playlist_prefetched:
            nxt = sch.peek_next()
            if nxt is not None and iids[nxt] != iid:
                nb = self._inputs[iids[nxt]]['buf']
                nb.set_gpu_ahead(GPU_AHEAD)
                nb.warm(0)
                self._playlist_prefetched = True
        self._idx = local
        self._seq_idx = local
        if logger.isEnabledFor(logging.DEBUG):
            torch.cuda.synchronize()
            _tg = time.perf_counter()
            got = entry['buf'].get(local)
            torch.cuda.synchronize()
            logger.debug(
                'PERF playlist get %s[%d]: %.2fms', iid, local,
                (time.perf_counter() - _tg) * 1000.0,
            )
        else:
            got = entry['buf'].get(local)
        self._splats = {iid: got}
        entry['buf'].warm(local)
        self._splat = compose_splats(self._splats)
        self._render_current()
        logger.debug('Playlist frame %s[%d]', iid, local)

    def _advance_play_order(self, steps: int) -> None:

        po = self._play_order
        for _ in range(steps):
            po.advance()
        self._render_play_order_frame()

    def _render_play_order_frame(self) -> None:

        po = self._play_order
        iid, _start, length = po.active_segment()
        local = po.local
        if iid != self._chain_active_iid:
            self._chain_active_iid = iid
            self.set_active_seq_input(iid)
            hook = self._playlist_switch_hook
            if hook is not None:
                hook(iid)
        fsync = self._playlist_frame_sync
        if fsync is not None:
            fsync(iid, local, length)
        entry = self._inputs[self._active_id]
        bidx = po.buf_idx()
        self._idx = bidx
        self._seq_idx = local

        if local == 0 and RANDOM_JUMP_PREWARM and self._playing:
            self._prewarm_jump(bidx)

        if logger.isEnabledFor(logging.DEBUG):
            torch.cuda.synchronize()
            _t = time.perf_counter()
            got = entry['buf'].get(bidx)
            torch.cuda.synchronize()
            _ms = (time.perf_counter() - _t) * 1000.0
            logger.debug(
                'PERF playorder get %s %s[%d] buf=%d: %.2fms resident=%d',
                'JUMP' if local == 0 else 'seq', iid, local, bidx, _ms,
                entry['buf'].gpu_resident_count,
            )
        else:
            got = entry['buf'].get(bidx)
        entry['buf'].warm(bidx)
        self._splats = {self._active_id: got}
        self._splat = compose_splats(self._splats)
        self._render_current()

    def _chain_seg_at(self, idx: int) -> tuple[str, int, int]:

        seg = self._chain_segments[0]
        for s in self._chain_segments:
            if idx >= s[1]:
                seg = s
            else:
                break
        return seg

    def _sync_chain_segment(self) -> None:

        iid, start, length = self._chain_seg_at(self._idx)
        local = self._idx - start
        if iid != self._chain_active_iid:
            self._chain_active_iid = iid
            self.set_active_seq_input(iid)
            hook = self._playlist_switch_hook
            if hook is not None:
                hook(iid)
        fsync = self._playlist_frame_sync
        if fsync is not None:
            fsync(iid, local, length)

    def _clear_message_overlay(self) -> None:
        self._message_overlay = ''
        self._render_current()

    def _update_cam(self) -> None:
        from process.camera import build_K
        is_ortho = self._ortho_active is not None
        self._camera_model = 'ortho' if is_ortho else 'pinhole'
        self._K = build_K(self._cam, self._w, self._h, ortho=is_ortho)
        self._viewmat = _viewmat_from_cam(self._cam)
        self._cam_dirty = True
        self._render_current()
