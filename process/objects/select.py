import logging

from PySide6.QtCore import Qt

from process.objects.keys import isolate_object
from process.objects.list_provider import build_object_list
from process.objects.playback_select import (
    active_input_id, notify_pause_required, seek_to_input, selection_allowed,
)

logger = logging.getLogger(__name__)

def _select_chain_object(win) -> None:

    itc = getattr(win, '_input_transform', None)
    if itc is None:
        return
    cid = next(iter(getattr(win, '_inputs', {})), None)
    if cid is not None:
        itc.select(cid)

def request_object_selection(win, index: int) -> None:
    segs = getattr(win, '_chain_segments', None)
    if segs:
        if not (0 <= index < len(segs)):
            return
        iid = segs[index][0]
        if not selection_allowed(win, iid):
            notify_pause_required(win)
            return
        if iid != active_input_id(win):
            seek_to_input(win, iid)
        _select_chain_object(win)
        return
    if getattr(win, '_scheduler', None) is not None:
        ids = list(getattr(win, '_inputs', {}))
        if not (0 <= index < len(ids)):
            return
        iid = ids[index]
        if not selection_allowed(win, iid):
            notify_pause_required(win)
            return
        if iid != active_input_id(win):
            seek_to_input(win, iid)
        itc = getattr(win, '_input_transform', None)
        if itc is not None:
            itc.select(iid)
        return
    isolate_object(win, index)

class ObjectListMouseHandler:

    def __init__(self, window) -> None:
        self._window = window

    def attach(self) -> None:
        handlers = getattr(self._window, '_mouse_handlers', None)
        if handlers is None:
            return
        handlers.insert(0, self.handle)

    def _hit_index(self, mx: float, my: float) -> int | None:
        rows = getattr(self._window._widget, '_object_rows', None) or []
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
        request_object_selection(self._window, index)
        return True

def register_objects(window) -> ObjectListMouseHandler | None:
    window._object_list_provider = lambda: build_object_list(window)
    if not window.input_ids():
        return None
    handler = ObjectListMouseHandler(window)
    handler.attach()
    logger.info('Object list selector attached')
    return handler
