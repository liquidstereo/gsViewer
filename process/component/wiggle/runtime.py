import logging

from process.component.random.wrappers import AttrRandomApplier
from process.component.wiggle.engine import noise_type_options
from process.component.wiggle.settings import (
    AMOUNT_RANGE, GAIN_RANGE, INTERVAL_RANGE, SEED_RANGE, SOFTNESS_RANGE,
    THRESHOLD_RANGE, WiggleComponent,
)

logger = logging.getLogger(__name__)

_FLOAT_PARAMS = {
    'interval': INTERVAL_RANGE,
    'seed': SEED_RANGE,
    'amount': AMOUNT_RANGE,
    'gain': GAIN_RANGE,
    'threshold': THRESHOLD_RANGE,
    'softness': SOFTNESS_RANGE,
}

def _clamp(value: float, vrange: tuple) -> float:
    lo, hi = float(vrange[0]), float(vrange[1])
    return min(hi, max(lo, value))

class WiggleConsoleContributor:

    console_key: str = 'wiggle'

    def __init__(self, component) -> None:
        self.component = component

        self.system = component

    def snapshot(self) -> dict:
        return self.component.snapshot()

    def value_hints(self) -> dict:
        return {
            'noise_type': ', '.join(noise_type_options()),
            'interval': 'seconds sharing one value (0 = per-frame)',
        }

    def apply(self, values: dict) -> None:
        if not isinstance(values, dict):
            return
        nt = values.get('noise_type')
        if isinstance(nt, str) and nt in noise_type_options():
            self.component.noise_type = nt
        for key, vrange in _FLOAT_PARAMS.items():
            v = values.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                setattr(self.component, key, _clamp(float(v), vrange))

def register_wiggle_console(window) -> None:
    contributors = getattr(window, '_console_contributors', None)
    if contributors is None:
        contributors = []
        window._console_contributors = contributors
    contributors.append(WiggleConsoleContributor(window._wiggle_component))

def attach_wiggle_component(window) -> None:
    component = WiggleComponent()
    window._wiggle_component = component
    window._attr_random = AttrRandomApplier(component)
    register_wiggle_console(window)
    processors = getattr(window, '_frame_processors', None)
    if processors is None:
        processors = []
        window._frame_processors = processors
    processors.insert(0, _make_frame_processor(window))

def _make_frame_processor(window):

    def _process(splat):
        applier = getattr(window, '_attr_random', None)
        if applier is not None:
            skip = getattr(window, '_attr_active_edit', None)
            applier.apply_frame(getattr(window, '_anim_tick', 0), skip)
        return splat

    return _process
