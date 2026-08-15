import logging

from configs.settings import PLAYBACK_FPS as _PLAYBACK_FPS

logger = logging.getLogger(__name__)

DEFAULT_FREQ = 2.0
DEFAULT_DAMPING = 0.5
DEFAULT_FPS = float(_PLAYBACK_FPS)
FREQ_RANGE = (0.01, 20.0)
DAMPING_RANGE = (0.0, 4.0)

SUBSTEP_DT = 0.008

SUBSTEP_SAFETY = 0.15

MAX_SUBSTEPS = 512

SNAP_DT = 0.25

class SpringComponent:

    __slots__ = ('freq', 'damping', 'fps', 'states')

    def __init__(self) -> None:
        self.freq: float = DEFAULT_FREQ
        self.damping: float = DEFAULT_DAMPING
        self.fps: float = DEFAULT_FPS
        self.states: dict = {}

    def set_freq(self, value: float) -> None:
        lo, hi = FREQ_RANGE
        self.freq = min(hi, max(lo, float(value)))

    def set_damping(self, value: float) -> None:
        lo, hi = DAMPING_RANGE
        self.damping = min(hi, max(lo, float(value)))

    def reset(self) -> None:
        self.freq = DEFAULT_FREQ
        self.damping = DEFAULT_DAMPING
        self.fps = DEFAULT_FPS
        self.states.clear()

    def snapshot(self) -> dict:
        return {
            'freq': float(self.freq),
            'damping': float(self.damping),
        }
