import logging

from process.component.wiggle.engine import (
    frame_group, noise_type_options, output_value, shape_value)
from process.console.reload import dump_attrs, reapply_attrs

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 0.0
DEFAULT_SEED = 0.123
DEFAULT_AMOUNT = 0.5
DEFAULT_GAIN = 1.0
DEFAULT_THRESHOLD = 0.0
DEFAULT_SOFTNESS = 0.0
DEFAULT_NOISE_TYPE = 'uniform'

NOISE_FREQ = 1.0
NOISE_SPEED = 1.0
NOISE_OCTAVES = 2

INTERVAL_RANGE = (0.0, 10.0)
SEED_RANGE = (0.0, 10.0)
AMOUNT_RANGE = (0.0, 1.0)
GAIN_RANGE = (0.0, 10.0)
THRESHOLD_RANGE = (0.0, 1.0)
SOFTNESS_RANGE = (0.0, 1.0)

_DEFAULT_MAP = {
    'interval': 'DEFAULT_INTERVAL',
    'seed': 'DEFAULT_SEED',
    'amount': 'DEFAULT_AMOUNT',
    'gain': 'DEFAULT_GAIN',
    'threshold': 'DEFAULT_THRESHOLD',
    'softness': 'DEFAULT_SOFTNESS',
    'noise_type': 'DEFAULT_NOISE_TYPE',
}
_DEFAULT_INTS = ()

class WiggleComponent:

    def __init__(self) -> None:
        self.interval: float = DEFAULT_INTERVAL
        self.seed: float = DEFAULT_SEED
        self.amount: float = DEFAULT_AMOUNT
        self.gain: float = DEFAULT_GAIN
        self.threshold: float = DEFAULT_THRESHOLD
        self.softness: float = DEFAULT_SOFTNESS
        self.noise_type: str = DEFAULT_NOISE_TYPE
        self.noise_freq: float = NOISE_FREQ
        self.noise_speed: float = NOISE_SPEED
        self.noise_octaves: int = NOISE_OCTAVES

        self.show_ui: bool = False

    def frame_group(self, frame_idx: int) -> int:
        return frame_group(self.interval, frame_idx)

    def shape(
        self, base: float, vmin: float, vmax: float, *keys: object,
    ) -> float:
        return shape_value(self, base, vmin, vmax, *keys)

    def random_output(self, group: int) -> float:
        return output_value(self, group)

    def reset(self) -> None:
        self.interval = DEFAULT_INTERVAL
        self.seed = DEFAULT_SEED
        self.amount = DEFAULT_AMOUNT
        self.gain = DEFAULT_GAIN
        self.threshold = DEFAULT_THRESHOLD
        self.softness = DEFAULT_SOFTNESS
        self.noise_type = DEFAULT_NOISE_TYPE

    def snapshot(self) -> dict:
        return {
            'noise_type': str(self.noise_type),
            'interval': float(self.interval),
            'seed': float(self.seed),
            'amount': float(self.amount),
            'gain': float(self.gain),
            'threshold': float(self.threshold),
            'softness': float(self.softness),
        }

    def apply_defaults(self, module) -> None:
        reapply_attrs(self, module, _DEFAULT_MAP, _DEFAULT_INTS)

    def dump_defaults(self, module) -> None:
        dump_attrs(self, module, _DEFAULT_MAP)

__all__ = ['WiggleComponent', 'noise_type_options']
