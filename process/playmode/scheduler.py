import random

PLAYLIST_MODES: tuple[str, ...] = ('single', 'shuffle', 'random')
LOOP_FALLBACK_MODES: tuple[str, ...] = ('shuffle', 'random')

def is_playlist(mode: str, n_inputs: int) -> bool:
    if mode not in PLAYLIST_MODES:
        return False
    if n_inputs <= 1 and mode != 'single':
        return False
    return True

class PlayOrder:

    def __init__(
        self, segments: list, mode: str, seed: int | None = None,
    ) -> None:
        self.segments = segments
        self.n = max(1, len(segments))
        self.mode = mode
        self.rng = random.Random(seed)
        self.local = 0
        self.order = self._make_order()
        self.pos = 0

    def _make_order(self) -> list:
        idx = list(range(self.n))
        if self.mode == 'shuffle':
            self.rng.shuffle(idx)
            return idx
        if self.mode == 'random':
            return [self.rng.randrange(self.n)]
        return idx

    def seg_index(self) -> int:
        return self.order[self.pos]

    def active_segment(self) -> tuple:
        return self.segments[self.seg_index()]

    def buf_idx(self) -> int:
        _iid, start, _length = self.active_segment()
        return start + self.local

    def peek_next_seg_index(self) -> int | None:
        if self.mode == 'shuffle' and self.pos + 1 < len(self.order):
            return self.order[self.pos + 1]
        return None

    def advance(self) -> None:
        self.local += 1
        _iid, _start, length = self.active_segment()
        if self.local < length:
            return
        self.local = 0
        if self.mode == 'random':
            self.order = [self.rng.randrange(self.n)]
            self.pos = 0
            return
        self.pos += 1
        if self.pos >= len(self.order):
            self.order = self._make_order()
            self.pos = 0

class PlaylistScheduler:

    def __init__(
        self, lengths: list[int], mode: str, seed: int | None = None,
    ) -> None:
        self.lengths = [max(1, n) for n in lengths]
        self.mode = self._fallback_mode(mode, len(self.lengths))
        self.rng = random.Random(seed)
        self.local = 0
        self.stopped = False
        self.order = self._make_order()
        self.pos = 0

    def _fallback_mode(self, mode: str, n: int) -> str:
        if n <= 1 and mode in LOOP_FALLBACK_MODES:
            return 'single'
        return mode

    def _make_order(self) -> list[int]:
        idx = list(range(len(self.lengths)))
        if self.mode == 'shuffle':
            self.rng.shuffle(idx)
        elif self.mode == 'random':
            return [self.rng.randrange(len(self.lengths))]
        return idx

    def active(self) -> int:
        return self.order[self.pos]

    def peek_next(self) -> int | None:
        if self.stopped or self.mode in ('single', 'random'):
            return None
        if self.mode == 'chain':
            return self.order[(self.pos + 1) % len(self.order)]
        if self.mode == 'shuffle':
            if self.pos + 1 < len(self.order):
                return self.order[self.pos + 1]
            return None
        return None

    def jump_to(self, input_index: int) -> None:
        if not (0 <= input_index < len(self.lengths)):
            return
        if input_index in self.order:
            self.pos = self.order.index(input_index)
        else:
            self.order = [input_index]
            self.pos = 0
        self.local = 0
        self.stopped = False

    def tick(self) -> None:
        if self.stopped:
            return
        self.local += 1
        if self.local < self.lengths[self.active()]:
            return
        self._advance()

    def _advance(self) -> None:
        self.local = 0
        if self.mode == 'random':
            self.order = [self.rng.randrange(len(self.lengths))]
            self.pos = 0
            return
        self.pos += 1
        if self.pos < len(self.order):
            return
        if self.mode == 'single':
            self.pos = len(self.order) - 1
            self.local = self.lengths[self.active()] - 1
            self.stopped = True
        elif self.mode == 'chain':
            self.pos = 0
        elif self.mode == 'shuffle':
            self.order = self._make_order()
            self.pos = 0
