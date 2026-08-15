import logging

from configs.settings import PLAYBACK_FPS as _PLAYBACK_FPS

logger = logging.getLogger(__name__)

DEFAULT_SCALE = 1.0
DEFAULT_MODE = 'linear'
DEFAULT_FPS = float(_PLAYBACK_FPS)
TIME_MODES = ('linear',)
SCALE_RANGE = (0.0, 1000.0)

class TimeComponent:

    __slots__ = ('scale', 'mode', 'fps')

    def __init__(self) -> None:
        self.scale: float = DEFAULT_SCALE
        self.mode: str = DEFAULT_MODE
        self.fps: float = DEFAULT_FPS

    def set_scale(self, value: float) -> None:
        lo, hi = SCALE_RANGE
        self.scale = min(hi, max(lo, float(value)))

    def set_mode(self, mode: str) -> None:
        if mode in TIME_MODES:
            self.mode = mode
        else:
            logger.warning('Invalid time mode ignored: %r', mode)

    def reset(self) -> None:
        self.scale = DEFAULT_SCALE
        self.mode = DEFAULT_MODE
        self.fps = DEFAULT_FPS

    def snapshot(self) -> dict:
        return {
            'scale': float(self.scale),
            'mode': str(self.mode),
        }
