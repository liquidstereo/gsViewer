import logging

from configs.settings import PLAYBACK_FPS
from process.component.random.engine import (
    random_output_value, scale_output_value, shape_random_value)

logger = logging.getLogger(__name__)

_noise_mod = None
_noise_tried: bool = False

def _load_noise():
    global _noise_mod, _noise_tried
    if not _noise_tried:
        _noise_tried = True
        try:
            from process.component import noise as noises
            _noise_mod = noises
        except ImportError:
            _noise_mod = None
    return _noise_mod

def noise_type_options() -> tuple:
    mod = _load_noise()
    if mod is None:
        return ('uniform',)
    return ('uniform',) + tuple(mod.NOISE_TYPES)

def group_length(interval: float) -> int:
    return max(1, round(float(interval) * PLAYBACK_FPS))

def frame_group(interval: float, frame_idx: int) -> int:
    return int(frame_idx) // group_length(interval)

def shape_value(
    component, base: float, vmin: float, vmax: float, *keys: object,
) -> float:
    return shape_random_value(
        base, vmin, vmax, component.amount, component.gain,
        component.threshold, component.softness, component.seed, *keys)

def output_value(component, group: int) -> float:
    mod = None if component.noise_type == 'uniform' else _load_noise()
    if mod is None:
        return random_output_value(
            component.amount, component.gain, component.threshold,
            component.softness, component.seed, '__random_output__', group)
    t = group * group_length(component.interval) / PLAYBACK_FPS
    v = mod.scalar(
        component.noise_type, t, component.noise_freq,
        component.noise_speed, component.noise_octaves, component.seed)
    return scale_output_value(component.amount, component.gain, v)
