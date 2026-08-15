import logging
from typing import Callable

logger = logging.getLogger(__name__)

class KeyframeSequence:

    def __init__(
        self,
        to_json: Callable[[dict], dict],
        from_json: Callable[[dict], dict],
    ) -> None:
        self._to_json = to_json
        self._from_json = from_json
        self._items: list[dict] = []
        self._cursor: int = -1

    def count(self) -> int:
        return len(self._items)

    def items(self) -> list[dict]:
        return self._items

    def cursor(self) -> int:
        return self._cursor

    def set_cursor(self, idx: int) -> None:
        self._cursor = idx

    def add(self, item: dict) -> int:
        self._items.append(item)
        return len(self._items)

    def remove_last(self) -> bool:
        if not self._items:
            return False
        self._items.pop()
        if self._cursor >= len(self._items):
            self._cursor = -1
        return True

    def clear(self) -> None:
        self._items.clear()
        self._cursor = -1

    def goto(self, delta: int) -> dict | None:
        n = len(self._items)
        if n == 0:
            return None
        if self._cursor == -1:
            self._cursor = 0 if delta > 0 else n - 1
        else:
            self._cursor = (self._cursor + delta) % n
        return self._items[self._cursor]

    def snapshot(self) -> tuple[list[dict], int]:
        return list(self._items), self._cursor

    def restore(self, snap: tuple[list[dict], int]) -> None:
        items, cursor = snap
        self._items = list(items)
        self._cursor = cursor

    def to_list(self) -> list[dict]:
        return [self._to_json(it) for it in self._items]

    def from_list(self, data: list[dict]) -> None:
        self._items = [self._from_json(d) for d in data]
        self._cursor = -1
