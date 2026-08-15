import logging

import numpy as np
from PySide6.QtCore import QTimer

from process.component.region_volume.settings import (
    REGION_VOLUME_KF_ANIM_DURATION, REGION_VOLUME_KF_ANIM_EASING, REGION_VOLUME_KF_ANIM_FPS,
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

def _reorthogonalize(R: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(R)
    R2 = u @ vt
    if np.linalg.det(R2) < 0.0:
        u[:, -1] *= -1.0
        R2 = u @ vt
    return R2.astype(np.float32)

class RegionVolumeKeyframeAnimator:

    def __init__(self, window, plugin) -> None:
        self._window = window
        self._plugin = plugin
        self.duration_ms: int = REGION_VOLUME_KF_ANIM_DURATION
        self._n_steps = max(
            1,
            REGION_VOLUME_KF_ANIM_DURATION * REGION_VOLUME_KF_ANIM_FPS // _MS_PER_SEC,
        )
        self._easing = _EASING.get(
            REGION_VOLUME_KF_ANIM_EASING, _ease_in_out,
        )
        self._step_idx: int = 0
        self._src: dict | None = None
        self._dst: dict | None = None
        self._src_scalars: dict = {}
        self._dst_scalars: dict = {}
        self._timer = QTimer(window)
        self._timer.setInterval(
            max(1, _MS_PER_SEC // REGION_VOLUME_KF_ANIM_FPS),
        )
        self._timer.timeout.connect(self._step)

    def start(self, dst_item: dict) -> None:
        region = self._plugin.region
        self._src = {
            'center':   region.center.astype(np.float32).copy(),
            'size':     region.size.astype(np.float32).copy(),
            'rotation': region.rotation.astype(np.float32).copy(),
            'softness': float(region.softness),
        }
        self._dst = {
            'center':   np.asarray(
                dst_item['center'], dtype=np.float32,
            ).copy(),
            'size':     np.asarray(
                dst_item['size'], dtype=np.float32,
            ).copy(),
            'rotation': np.asarray(
                dst_item['rotation'], dtype=np.float32,
            ).copy(),
            'softness': float(dst_item['softness']),
        }
        self._src_scalars = dict(
            getattr(self._plugin, 'reveal_scalars', {}) or {},
        )
        self._dst_scalars = dict(dst_item.get('scalars', {}) or {})
        self._step_idx = 0
        if not self._timer.isActive():
            self._timer.start()
        logger.debug(
            'RegionVolume keyframe animation started (%d steps, %s)',
            self._n_steps, REGION_VOLUME_KF_ANIM_EASING,
        )

    def set_duration_ms(self, value: float) -> None:
        ms = max(1, int(value))
        self.duration_ms = ms
        self._n_steps = max(
            1, ms * REGION_VOLUME_KF_ANIM_FPS // _MS_PER_SEC,
        )

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self._step_idx = 0

    def _step(self) -> None:
        self._step_idx += 1
        raw = min(self._step_idx / self._n_steps, 1.0)
        t = self._easing(raw)
        inv = 1.0 - t
        region = self._plugin.region
        region.center = (
            self._src['center'] * inv + self._dst['center'] * t
        ).astype(np.float32)
        region.size = (
            self._src['size'] * inv + self._dst['size'] * t
        ).astype(np.float32)
        R_lerp = self._src['rotation'] * inv + self._dst['rotation'] * t
        region.rotation = _reorthogonalize(R_lerp)
        region.softness = float(
            self._src['softness'] * inv + self._dst['softness'] * t,
        )
        self._lerp_scalars(inv, t)
        if hasattr(self._window, '_widget'):
            self._window._widget.update()
        if self._step_idx >= self._n_steps:
            self._timer.stop()
            self._plugin.save_region()
            logger.debug('RegionVolume keyframe animation complete')

    def _lerp_scalars(self, inv: float, t: float) -> None:
        if not self._dst_scalars:
            return
        cb = getattr(self._plugin, 'on_scalar_update', None)
        if not callable(cb):
            return
        for key, dst_val in self._dst_scalars.items():
            src_val = self._src_scalars.get(key, dst_val)
            cb(key, src_val * inv + dst_val * t)
