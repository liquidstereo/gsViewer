import logging
from typing import Callable

from PySide6.QtCore import QTimer

logger = logging.getLogger(__name__)

_MS_PER_SEC = 1000

def _ease_in(t: float) -> float:
    return t * t

def _ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) ** 2

def _ease_in_out(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)

_EASING: dict = {
    'EasyEase': _ease_in_out,
    'EaseIn':   _ease_in,
    'EaseOut':  _ease_out,
}

class KeyframeAnimator:

    def __init__(
        self,
        window,
        capture: Callable[[], dict | None],
        apply: Callable[[dict], None],
        interpolate: Callable[[dict, dict, float], dict],
        default_ms: int,
        fps: int = 60,
        easing: str = 'EasyEase',
    ) -> None:
        self._window = window
        self._capture = capture
        self._apply = apply
        self._interpolate = interpolate
        self._fps = max(1, int(fps))
        self.duration_ms: int = max(1, int(default_ms))
        self._n_steps = self._steps_for(self.duration_ms)
        self._cur_steps = self._n_steps
        self._easing = _EASING.get(easing, _ease_in_out)
        self._step_idx: int = 0
        self._src: dict | None = None
        self._dst: dict | None = None
        self._timer = QTimer(window)
        self._timer.setInterval(max(1, _MS_PER_SEC // self._fps))
        self._timer.timeout.connect(self._step)

    def _steps_for(self, ms: int) -> int:
        return max(1, int(ms) * self._fps // _MS_PER_SEC)

    def set_duration_ms(self, value: float) -> None:
        self.duration_ms = max(1, int(round(value)))
        self._n_steps = self._steps_for(self.duration_ms)

    def start(self, dst_item: dict) -> None:
        src = self._capture()
        if src is None:
            return
        self._src = src
        self._dst = dst_item
        dur = int(dst_item.get('duration', 0) or 0)
        self._cur_steps = (
            self._steps_for(dur) if dur > 0 else self._n_steps
        )
        self._step_idx = 0
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self._step_idx = 0

    def _step(self) -> None:
        self._step_idx += 1
        t = self._easing(min(self._step_idx / self._cur_steps, 1.0))
        self._apply(self._interpolate(self._src, self._dst, t))
        if self._step_idx >= self._cur_steps:
            self._timer.stop()
