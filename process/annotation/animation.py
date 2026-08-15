import logging

from PySide6.QtCore import QTimer

from configs.settings_annot import (
    ANNOT_ANIM_DURATION,
    ANNOT_ANIM_FPS,
    ANNOT_ANIM_EASING,
)

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

class AnnotationAnimator:

    def __init__(self, win) -> None:
        self._win = win

        self.duration_ms: int = ANNOT_ANIM_DURATION
        self._n_steps = self._steps_for(self.duration_ms)

        self._cur_steps = self._n_steps
        self._easing = _EASING.get(ANNOT_ANIM_EASING, _ease_in_out)
        self._step_idx: int = 0
        self._src: dict | None = None
        self._dst: dict | None = None
        self._timer = QTimer(win)
        self._timer.setInterval(max(1, _MS_PER_SEC // ANNOT_ANIM_FPS))
        self._timer.timeout.connect(self._step)

    @staticmethod
    def _steps_for(duration_ms: int) -> int:
        return max(1, int(duration_ms) * ANNOT_ANIM_FPS // _MS_PER_SEC)

    def set_duration_ms(self, value: float) -> None:
        self.duration_ms = max(1, int(round(value)))
        self._n_steps = self._steps_for(self.duration_ms)
        logger.info('Annotation anim duration: %d ms', self.duration_ms)

    def start(self, dst_item: dict) -> None:
        dur = int(dst_item.get('duration', 0) or 0)
        self._cur_steps = (
            self._steps_for(dur) if dur > 0 else self._n_steps
        )
        cam = self._win._cam
        self._src = {
            'target':    cam['target'].copy(),
            'azimuth':   float(cam['azimuth']),
            'elevation': float(cam['elevation']),
            'distance':  float(cam['distance']),
        }
        self._dst = {
            'target':    dst_item.get('target', dst_item['pos']).copy(),
            'azimuth':   float(dst_item['azimuth']),
            'elevation': float(dst_item['elevation']),
            'distance':  float(dst_item['distance']),
        }
        self._step_idx = 0
        if not self._timer.isActive():
            self._timer.start()
        logger.debug(
            'Annotation animation started (%d steps, %s)',
            self._cur_steps, ANNOT_ANIM_EASING,
        )

    def _step(self) -> None:
        self._step_idx += 1
        t = self._easing(
            min(self._step_idx / self._cur_steps, 1.0)
        )
        inv = 1.0 - t
        cam = self._win._cam
        cam['target'] = (
            self._src['target'] * inv + self._dst['target'] * t
        )
        cam['azimuth'] = (
            self._src['azimuth'] * inv + self._dst['azimuth'] * t
        )
        cam['elevation'] = (
            self._src['elevation'] * inv + self._dst['elevation'] * t
        )
        cam['distance'] = (
            self._src['distance'] * inv + self._dst['distance'] * t
        )
        self._win._update_cam()
        if self._step_idx >= self._cur_steps:
            self._timer.stop()
            logger.debug('Annotation animation complete')
