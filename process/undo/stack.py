import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

_Entry = tuple[str, Callable[[], None], Callable[[], None]]

class UndoStack:

    def __init__(self, limit: int = 100) -> None:
        self._undo: list[_Entry] = []
        self._redo: list[_Entry] = []
        self._limit: int = max(1, int(limit))

    def push(
        self, label: str,
        undo_fn: Callable[[], None],
        redo_fn: Callable[[], None],
    ) -> None:
        self._undo.append((label, undo_fn, redo_fn))
        if len(self._undo) > self._limit:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> str | None:
        if not self._undo:
            return None
        entry = self._undo.pop()
        entry[1]()
        self._redo.append(entry)
        return entry[0]

    def redo(self) -> str | None:
        if not self._redo:
            return None
        entry = self._redo.pop()
        entry[2]()
        self._undo.append(entry)
        return entry[0]

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
