import logging

logger = logging.getLogger(__name__)

DEFAULT_AMOUNT = 1.0
DEFAULT_SEED = 0.0
DEFAULT_MODE = 'uniform'
DEFAULT_REROLL = 0
RANDOM_MODES = ('uniform', 'gaussian')
AMOUNT_RANGE = (0.0, 1000.0)
SEED_RANGE = (0.0, 999999.0)

DEFAULT_RANDOM_DIST = 1.0

class RandomComponent:

    __slots__ = ('amount', 'seed', 'mode', 'reroll')

    def __init__(self) -> None:
        self.amount: float = DEFAULT_AMOUNT
        self.seed: float = DEFAULT_SEED
        self.mode: str = DEFAULT_MODE
        self.reroll: int = DEFAULT_REROLL

    def set_amount(self, value: float) -> None:
        lo, hi = AMOUNT_RANGE
        self.amount = min(hi, max(lo, float(value)))

    def set_seed(self, value: float) -> None:
        lo, hi = SEED_RANGE
        self.seed = min(hi, max(lo, float(value)))

    def set_mode(self, mode: str) -> None:
        if mode in RANDOM_MODES:
            self.mode = mode
        else:
            logger.warning('Invalid random mode ignored: %r', mode)

    def set_reroll(self, value: int) -> None:
        self.reroll = max(0, int(value))

    def bump_reroll(self) -> None:
        self.reroll = int(self.reroll) + 1

    def reset(self) -> None:
        self.amount = DEFAULT_AMOUNT
        self.seed = DEFAULT_SEED
        self.mode = DEFAULT_MODE
        self.reroll = DEFAULT_REROLL

    def snapshot(self) -> dict:
        return {
            'amount': float(self.amount),
            'seed': float(self.seed),
            'mode': str(self.mode),
            'reroll': int(self.reroll),
        }
