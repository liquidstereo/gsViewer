import logging
import math
import time

import torch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from configs.settings import (
    AUTO_START, BUFFER_FRAMES_RATIO, PLAYBACK_FPS, PLAYBACK_MAX_CATCHUP,
    RANDOM_GPU_AHEAD, WINDOW_TITLE,
)
from configs.settings_overlay import BUFFER_STAGES, SAVE_FINALIZE_MESSAGE
from configs.settings_camera import TURNTABLE_SPEED
from process.camera import _viewmat_from_cam
from process.data.compose import compose_splats
from process.perf.present import PRESENT_PERF, note_clamp, present_tick
from process.playmode import (
    PlaylistScheduler, PlayOrder, is_playlist,
)

logger = logging.getLogger(__name__)

class PlaybackMixin:

    def _init_playback_state(
        self, inputs: dict, playback_mode: str,
        chain_segments: list | None,
    ) -> None:
        self._total_frames = max(len(v['files']) for v in inputs.values())
        self._playback_mode = playback_mode
        self._scheduler = (
            PlaylistScheduler(
                [len(v['files']) for v in inputs.values()], playback_mode,
            )
            if is_playlist(playback_mode, len(inputs)) else None
        )
        self._playlist_prefetched = False
        self._chain_segments = chain_segments or []
        self._chain_active_iid = None

        self._play_order = (
            PlayOrder(self._chain_segments, playback_mode)
            if (self._chain_segments and playback_mode == 'random') else None
        )

    def _load_initial_splat(self) -> None:
        self._splats = {}
        if self._scheduler is not None:
            entry = self._inputs[self._active_id]
            entry['buf'].warm(0)
            self._splats[self._active_id] = entry['buf'].get(0)
        elif self._play_order is not None:

            entry = self._inputs[self._active_id]

            entry['buf'].set_gpu_ahead(RANDOM_GPU_AHEAD)
            bidx = self._play_order.buf_idx()
            entry['buf'].warm(bidx)
            self._splats[self._active_id] = entry['buf'].get(bidx)
        else:
            for iid, entry in self._inputs.items():
                entry['buf'].warm(0)
                self._splats[iid] = entry['buf'].get(0)
        self._splat = compose_splats(self._splats)

    def _begin_playback(self) -> None:
        if self._playing:
            return
        self._run_buffer_stages()

        self._wait_window_warm()

        for hook in self._prestart_hooks:
            try:
                hook()
            except Exception:
                logger.exception('Prestart hook error')
        self._start_or_wait_playback()

    def _run_buffer_stages(self) -> None:
        buffer_frames = self._buffer_frame_count()
        if buffer_frames <= 0:
            return
        self._buffering = True
        try:
            stages = len(BUFFER_STAGES)
            for i in range(buffer_frames):
                pct = int((i + 1) / buffer_frames * 100)
                si = min(i * stages // buffer_frames, stages - 1)
                self._set_buffer_stage(si + 1, BUFFER_STAGES[si], pct)
                self._render_current()
                QApplication.processEvents()
        finally:
            self._buffering = False

    def _start_or_wait_playback(self) -> None:

        if AUTO_START:
            self._playing = True
            self._reset_playback_clock()
            self._timer.start()
            self._run_playback_start_hooks()

            self._sync_audio_to_frame()
            return
        self._playing = False
        self._message_overlay = 'PRESS SPACE TO PLAY'
        self._message_overlay_timer.start()
        self._render_current()

    def _buffer_frame_count(self) -> int:

        if BUFFER_FRAMES_RATIO <= 0:
            return 0
        return max(1, round(self._total_frames * BUFFER_FRAMES_RATIO))

    def _set_buffer_stage(self, idx: int, label: str, pct: int) -> None:

        total = len(BUFFER_STAGES)
        self._buffer_message = f'[{idx}/{total}] {label}...({pct}%)'

    def _reset_playback_clock(self) -> None:

        now = time.perf_counter()
        self._last_frame_time = now
        self._last_tick_time = now

    def _on_first_paint(self) -> None:
        detail = self._ready_input_detail()

        log_note = (
            f' Logs will be saved to {self._log_path}.'
            if self._log_path is not None else ''
        )
        if self._start_time is not None:
            elapsed = time.perf_counter() - self._start_time
            mins = int(elapsed // 60)
            secs = elapsed - mins * 60
            if mins > 0:
                logger.info(
                    '%s Ready. Elapsed %d Min. %.3f Sec. (%s)%s',
                    WINDOW_TITLE, mins, secs, detail, log_note
                )
            else:
                logger.info(
                    '%s Ready. Elapsed %.3f Sec. (%s)%s',
                    WINDOW_TITLE, secs, detail, log_note
                )

        if not self._playback_started:
            self._playback_started = True
            QTimer.singleShot(0, self._begin_playback)

    def _on_timer(self) -> None:

        if PRESENT_PERF:
            present_tick(self, time.perf_counter())

        now = time.perf_counter()

        if self._live_recording:
            self._capture_live_frame()

        if self._buffering:
            self._last_frame_time = now
            self._last_tick_time = now
            return

        if self._save_dir is not None:
            self._advance_save_frame()
            return
        tick_dt = now - self._last_tick_time
        self._last_tick_time = now

        max_catchup = self._playback_catchup or PLAYBACK_MAX_CATCHUP
        steps = int((now - self._last_frame_time) * PLAYBACK_FPS)
        if steps > max_catchup:

            if PRESENT_PERF:
                note_clamp(self, now - self._last_frame_time, max_catchup)

            steps = max_catchup
            self._last_frame_time = now
        elif steps > 0:
            self._last_frame_time += steps / PLAYBACK_FPS
        if steps > 0:

            self._anim_tick += steps
            self._log_vram_trend(steps)

        if (
            self._turntable and self._playing
            and self._ortho_active is None
        ):
            self._cam['azimuth'] -= math.radians(TURNTABLE_SPEED * tick_dt)
            self._viewmat = _viewmat_from_cam(self._cam)
            self._cam_dirty = True

        _cam_driver = self._camera_frame_driver
        if _cam_driver is not None and self._playing:
            _cam_driver(self, self._idx)

        if self._particles is not None and self._particles.active:
            self._render_current()
            return

        if self._scheduler is not None:
            if steps > 0:
                self._advance_playlist(steps)
            else:
                self._render_current()
            return

        if self._play_order is not None:
            if steps > 0:
                self._advance_play_order(steps)
            else:
                self._render_current()
            return

        clock = self._playback_clock_frame
        target = (
            clock() if (clock is not None and not self._chain_segments)
            else None
        )
        if target is not None:
            if target != self._idx:
                self.set_frame(target)
            else:
                self._render_current()
            return
        if steps <= 0:
            self._render_current()
            self._sync_audio_to_frame()
            return
        self.set_frame(self._idx + steps)
        self._sync_audio_to_frame()

    def _sync_audio_to_frame(self) -> None:

        if (self._chain_segments or self._scheduler is not None
                or self._play_order is not None):
            return
        fsync = self._playback_frame_sync
        entry = self._inputs.get(self._active_id)
        if fsync is None or entry is None:
            return
        count = max(1, len(entry['files']))
        local = self._seq_idx % count

        src = self._audio_timeline_source
        pos = src() if src is not None else None
        if pos is not None:
            local, count = pos

            if count <= 0:
                return
        elif count <= 1:

            return
        fsync(self._active_id, local, count)

    def _advance_save_frame(self) -> None:

        self._anim_tick += 1
        if (
            self._turntable and self._playing
            and self._ortho_active is None and PLAYBACK_FPS > 0
        ):
            self._cam['azimuth'] -= math.radians(
                TURNTABLE_SPEED / PLAYBACK_FPS
            )
            self._viewmat = _viewmat_from_cam(self._cam)
            self._cam_dirty = True

        _cam_driver = self._camera_frame_driver
        if _cam_driver is not None:
            _cam_driver(self, self._idx)
        if not self._save_frame_primed:
            self._save_frame_primed = True
            self._render_current()
            self._capture_save_frame()
            return
        if self._particles is not None and self._particles.active:
            self._render_current()
            self._capture_save_frame()
            return
        if self._scheduler is not None:
            self._advance_playlist(1)
            self._capture_save_frame()
            return
        if self._play_order is not None:
            self._advance_play_order(1)
            self._capture_save_frame()
            return
        self.set_frame(self._idx + 1)

        self._sync_audio_to_frame()
        self._capture_save_frame()

    def _show_finalizing_overlay(self) -> None:

        self._buffer_message = SAVE_FINALIZE_MESSAGE
        self._buffering = True
        self._render_current()
        QApplication.processEvents()

    def _pause_playback_for_mux(self) -> None:

        for hook in self._pause_hooks:
            try:
                hook(True)
            except Exception:
                logger.exception('Mux pause hook error')

    def _resume_playback_after_save(self) -> None:
        self._save_frame_primed = False
        self._playing = True
        self._reset_playback_clock()

        self._idx = 0

        if self._chain_segments:
            self._chain_active_iid = None
            self._sync_chain_segment()
        for hook in self._pause_hooks:
            try:
                hook(False)
            except Exception:
                logger.exception('Resume hook error')

    def _log_vram_trend(self, steps: int) -> None:

        if not logger.isEnabledFor(logging.DEBUG):
            return
        if self._anim_tick % 60 >= steps:
            return
        alloc = torch.cuda.memory_allocated() / 1048576.0
        resv = torch.cuda.memory_reserved() / 1048576.0
        logger.debug(
            'PERF VRAM tick=%d alloc=%.0fMB reserved=%.0fMB gpu_resident=%d',
            self._anim_tick, alloc, resv, self._buf.gpu_resident_count,
        )

    def _run_playback_start_hooks(self) -> None:
        if not self._playback_start_hooks:
            return
        for hook in self._playback_start_hooks:
            try:
                hook()
            except Exception:
                logger.exception('Playback start hook error')
        self._playback_start_hooks.clear()
