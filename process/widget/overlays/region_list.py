import logging

from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class RegionListMouseHandler:

    def __init__(self, window) -> None:
        self._window = window

    def attach(self) -> None:
        handlers = getattr(self._window, '_mouse_handlers', None)
        if handlers is None:
            return
        handlers.insert(0, self.handle)

    def _hit_index(self, mx: float, my: float) -> int | None:
        rows = getattr(self._window._widget, '_region_rows', None) or []
        for x, y, w, h, index in rows:
            if x <= mx <= x + w and y <= my <= y + h:
                return index
        return None

    def handle(self, kind: str, event) -> bool:
        if kind != 'press':
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        pos = event.position()
        index = self._hit_index(pos.x(), pos.y())
        if index is None:
            return False
        cb = getattr(self._window, '_region_select_cb', None)
        if cb is not None:
            cb(index)
        return True

def register_region_entry_source(window, items_fn, select_fn) -> None:
    sources = getattr(window, '_region_entry_sources', None)
    if sources is None:
        sources = []
        window._region_entry_sources = sources
    sources.append((items_fn, select_fn))

def _composite_region_items(window) -> list:
    out: list = []
    for items_fn, _ in getattr(window, '_region_entry_sources', ()):
        out.extend(items_fn())
    return out

def _composite_region_select(window, index: int) -> None:
    base = 0
    for items_fn, select_fn in getattr(window, '_region_entry_sources', ()):
        n = len(items_fn())
        if index < base + n:
            select_fn(index - base)
            return
        base += n

def register_region_list(window) -> RegionListMouseHandler:
    window._region_list_provider = lambda: _composite_region_items(window)
    window._region_select_cb = lambda i: _composite_region_select(window, i)
    handler = RegionListMouseHandler(window)
    handler.attach()
    logger.info('Region list selector attached')
    return handler
