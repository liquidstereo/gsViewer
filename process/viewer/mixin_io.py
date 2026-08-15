import logging
import time

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage

from configs.settings import (
    PLAYBACK_FPS, SAVE_JPG_QUALITY, SAVE_PNG_QUALITY, SAVE_WITH_OVERLAY,
)
from process.capture import grab_frame_for_save
from process.perf.collector import perf_push
from process.perf.present import PRESENT_PERF, note_save
from process.record import qimage_to_rgb_bytes
from process.record.quality import png_quality_value
from process.record.settings import DEFAULT_SAVE_FPS
from process.viewer.utils import write_image_to_file

logger = logging.getLogger(__name__)

class SaveRecordMixin:

    def _capture_save_frame(self) -> None:

        if self._save_dir is None or self._buffering:
            return
        arr = self._widget._image_arr
        if arr is None:
            return

        if not self._widget._live_rec_on:
            self._widget._live_rec_on = True
            self._live_blink.start(True)
        self._widget._live_rec_seconds = (
            (self._save_count + 1) / float(DEFAULT_SAVE_FPS))

        _dbg = logger.isEnabledFor(logging.DEBUG)
        _meas = _dbg or PRESENT_PERF
        _t0 = time.perf_counter() if _meas else 0.0
        self._auto_save(arr)
        self._record_save_audio_pos()
        if _meas:
            _ms = (time.perf_counter() - _t0) * 1000.0
            if _dbg:
                perf_push(self, save=_ms)
            if PRESENT_PERF:
                note_save(self, _ms)
        self._check_save_limit()

    def _record_save_audio_pos(self) -> None:

        entry = self._inputs.get(self._active_id)
        if entry is None:
            return
        count = max(1, len(entry['files']))
        self._save_audio_positions.append(
            (self._active_id, self._seq_idx % count, count))

    def _auto_save(self, arr: np.ndarray) -> None:
        if self._recorder is not None:
            self._record_frame(arr)
            return
        _dbg = logger.isEnabledFor(logging.DEBUG)
        _t0 = time.perf_counter() if _dbg else 0.0
        if SAVE_WITH_OVERLAY:
            img = grab_frame_for_save(self, arr)
        else:
            h, w, _ = arr.shape
            img = QImage(
                arr.data, w, h, w * 3,
                QImage.Format.Format_RGB888,
            ).copy()
        _t1 = time.perf_counter() if _dbg else 0.0
        ext = self._save_img_ext
        quality = (
            png_quality_value(self._save_quality, SAVE_PNG_QUALITY)
            if ext == 'png' else SAVE_JPG_QUALITY
        )
        fname = f'{self._save_stem}.{self._save_count:04d}.{ext}'
        out = self._save_dir / fname
        self._save_executor.submit(write_image_to_file, img, out, quality)
        if _dbg and self._save_count % 30 == 0:
            self._log_save_perf('image', _t0, _t1)

    def _record_frame(self, arr: np.ndarray) -> None:
        _dbg = logger.isEnabledFor(logging.DEBUG)
        _t0 = time.perf_counter() if _dbg else 0.0
        if SAVE_WITH_OVERLAY:
            img = grab_frame_for_save(self, arr)
            data = qimage_to_rgb_bytes(img)
        else:
            data = np.ascontiguousarray(arr).tobytes()
        _t1 = time.perf_counter() if _dbg else 0.0
        if self._save_executor is not None:
            self._save_executor.submit(self._recorder.write, data)
        else:
            self._recorder.write(data)
        if _dbg and self._save_count % 30 == 0:
            self._log_save_perf('recorder', _t0, _t1)

    def _log_save_perf(self, kind: str, t0: float, t1: float) -> None:

        grab_ms = (t1 - t0) * 1000.0
        enc_ms = (time.perf_counter() - t1) * 1000.0
        backlog = -1
        ex = self._save_executor
        if ex is not None:
            q = getattr(ex, '_work_queue', None)
            if q is not None:
                try:
                    backlog = q.qsize()
                except Exception:
                    backlog = -1
        logger.debug(
            'PERF save %s: grab %.2fms enc %.2fms backlog=%d count=%d '
            'overlay=%d',
            kind, grab_ms, enc_ms, backlog, self._save_count,
            int(SAVE_WITH_OVERLAY),
        )

    def _close_recorder(self, wait: bool = False) -> None:
        rec = self._recorder
        if rec is None:
            return
        self._recorder = None
        if wait:
            if self._save_executor is not None:
                try:
                    self._save_executor.shutdown(wait=True)
                except Exception:
                    logger.exception('Save executor flush error')
                self._save_executor = None
            rec.close()
            return
        if self._save_executor is not None:
            self._save_executor.submit(rec.close)
        else:
            rec.close()

    def _check_save_limit(self) -> None:
        self._save_count += 1
        if self._save_continuous or self._save_limit == 0:
            return
        if self._save_count >= self._save_limit:
            self._save_dir = None

            self._live_blink.stop(False)
            self._widget._live_rec_on = False
            self._widget._live_rec_seconds = None
            t_play_end = time.perf_counter()
            self._pause_playback_for_mux()
            self._show_finalizing_overlay()
            self._finalize_save_video_audio()
            self._flush_save_executor()
            self._buffering = False
            self._report_save_time_diff(t_play_end)
            logger.debug(
                'Auto-save complete: %d frames saved', self._save_count
            )
            if self._save_quit:
                self._playing = False
                QTimer.singleShot(0, self._save_quit_exit)
                return

            self._resume_playback_after_save()

    def _flush_save_executor(self) -> None:

        if self._save_executor is None:
            return
        try:
            self._save_executor.shutdown(wait=True)
        except Exception:
            logger.exception('Save executor flush error')
        self._save_executor = None

    def _report_save_time_diff(self, t_play_end: float) -> None:

        diff = time.perf_counter() - t_play_end
        minutes = int(diff // 60)
        seconds = diff - minutes * 60
        msg = (
            f'Output Saved. Save Time Difference From Playback: '
            f'{minutes:02d}:{seconds:06.3f} (mm:ss.sss)'
        )
        logger.info(msg)
        self._save_time_diff_msg = msg

    def _finalize_save_video_audio(self) -> None:
        has_recorder = self._recorder is not None
        out_file = self._save_out_file
        self._close_recorder(wait=has_recorder)
        if not has_recorder or out_file is None:
            return
        from process.record.mux import mux_audio

        positions = self._save_audio_positions
        live_provider = getattr(self, '_live_audio_segments', None)
        if (getattr(self, '_frame_index_mappers', None)
                and getattr(self, '_audio_sync', False)
                and getattr(self, '_audio_timeline_source', None) is None
                and live_provider is not None and positions):
            try:
                segments = live_provider(positions)
            except Exception:
                logger.exception('Save audio (jitter) provider error')
                segments = None
            self._save_audio_positions = []
            if segments:
                mux_audio(out_file, segments)
            return
        self._save_audio_positions = []
        provider = self._save_audio_segments
        if provider is None:
            return
        try:
            segments = provider()
        except Exception:
            logger.exception('Save audio provider error')
            return
        if not segments:
            return
        if self._save_continuous and PLAYBACK_FPS > 0:
            target = self._save_count / PLAYBACK_FPS
            segments = self._tile_segments_to_length(segments, target)
        mux_audio(out_file, segments)

    def _tile_segments_to_length(
        self,
        segments: list[tuple[str | None, float]],
        target: float,
    ) -> list[tuple[str | None, float]]:
        if target <= 0 or not segments:
            return segments
        total = sum(max(0.0, dur) for _, dur in segments)
        if total <= 0:
            return segments
        tiled: list[tuple[str | None, float]] = []
        acc = 0.0
        count = len(segments)
        idx = 0
        while acc < target:
            path, dur = segments[idx % count]
            dur = max(0.0, dur)
            idx += 1
            if dur <= 0:
                continue
            remain = target - acc
            if dur >= remain:
                tiled.append((path, remain))
                break
            tiled.append((path, dur))
            acc += dur
        return tiled

    def _save_quit_exit(self) -> None:
        self._close_recorder(wait=True)
        if self._save_executor is not None:
            try:
                self._save_executor.shutdown(wait=True)
            except Exception:
                logger.exception('Save executor flush error')
            self._save_executor = None
        self._force_exit()

    def _save_exit_note(self) -> str | None:

        if self._save_out_dir is None or self._save_count <= 0:
            return None
        word = 'frame' if self._save_count == 1 else 'frames'
        target = self._save_out_file or self._save_out_dir
        note = (
            f'Frame Export Complete. '
            f'({self._save_count} {word} to ./{target})'
        )
        if self._save_renamed is not None:
            orig, final = self._save_renamed
            note = (
                f'Renamed to \"./{final}\" to avoid name collision.'

                f'\n{note}'
            )
        return note
