import logging
import time

from PySide6.QtWidgets import QApplication

from configs.settings import (
    RANDOM_JUMP_MAX_WAIT_S, RANDOM_JUMP_POLL_S, RANDOM_JUMP_WARM_AHEAD,
    SETTLE_TIME, SLICE_REBUILD_MAX_WAIT_S,
    SLICE_REBUILD_POLL_S, SLICE_REBUILD_SETTLE_TICKS,
)

logger = logging.getLogger(__name__)

class ResliceBufferMixin:

    def _prewarm_jump(self, bidx: int) -> None:
        buf = self._inputs[self._active_id]['buf']
        if buf.is_gpu_resident(bidx):
            return
        resume = self._playing
        if resume:
            for hook in self._pause_hooks:
                try:
                    hook(True)
                except Exception:
                    logger.exception('Jump prewarm pause hook error')
        self._buffering = True
        try:
            buf.warm(bidx)
            target = RANDOM_JUMP_WARM_AHEAD
            deadline = time.perf_counter() + RANDOM_JUMP_MAX_WAIT_S
            while time.perf_counter() < deadline:
                warm_n = sum(
                    buf.is_gpu_resident(bidx + j) for j in range(target)
                )
                if warm_n >= target:
                    break
                self._render_current()
                QApplication.processEvents()
                time.sleep(RANDOM_JUMP_POLL_S)
        finally:
            self._buffering = False
        if resume:
            self._reset_playback_clock()
            for hook in self._pause_hooks:
                try:
                    hook(False)
                except Exception:
                    logger.exception('Jump prewarm resume hook error')

    def _rebuffer_after_reload(self) -> None:
        resume = self._playing
        if resume:
            for hook in self._pause_hooks:
                try:
                    hook(True)
                except Exception:
                    logger.exception('Rebuffer pause hook error')
        self._run_buffer_stages()
        self._wait_window_warm()
        if resume:
            self._reset_playback_clock()
            for hook in self._pause_hooks:
                try:
                    hook(False)
                except Exception:
                    logger.exception('Rebuffer resume hook error')

    def _wait_window_warm(self) -> None:
        self._buffering = True
        try:
            deadline = time.perf_counter() + SLICE_REBUILD_MAX_WAIT_S
            prev = -1
            stable = 0
            while time.perf_counter() < deadline:
                count = self._buf.gpu_resident_count
                if count == prev:
                    stable += 1
                    if stable >= SLICE_REBUILD_SETTLE_TICKS:
                        break
                else:
                    prev = count
                    stable = 0
                self._render_current()
                QApplication.processEvents()
                time.sleep(SLICE_REBUILD_POLL_S)

            extra_end = time.perf_counter() + SETTLE_TIME
            while time.perf_counter() < extra_end:
                self._render_current()
                QApplication.processEvents()
                time.sleep(SLICE_REBUILD_POLL_S)
        finally:
            self._buffering = False
