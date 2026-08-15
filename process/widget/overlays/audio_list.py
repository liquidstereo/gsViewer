import logging

from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class AudioListMouseHandler:

    def __init__(self, window) -> None:
        self._window = window

    def attach(self) -> None:
        handlers = getattr(self._window, '_mouse_handlers', None)
        if handlers is None:
            return
        handlers.insert(0, self.handle)

    def _hit_index(self, mx: float, my: float) -> int | None:
        rows = getattr(self._window._widget, '_audio_rows', None) or []
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
        cb = getattr(self._window, '_audio_select_cb', None)
        if cb is not None:
            cb(index)
        return True

def register_audio_list(window) -> AudioListMouseHandler:
    handler = AudioListMouseHandler(window)
    handler.attach()
    logger.info('Audio list selector attached')
    return handler
