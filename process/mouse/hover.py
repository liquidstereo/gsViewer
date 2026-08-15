import logging

from process.common import request_repaint
from process.handle import overlay_event
from process.widget.text_case import keep_case

logger = logging.getLogger(__name__)

class HoverNameMouseHandler:

    def __init__(self, window) -> None:
        self._window = window
        self._last: str = ''

    def attach(self) -> None:
        handlers = getattr(self._window, '_mouse_handlers', None)
        if handlers is None:
            return
        handlers.append(self.handle)

    def _resolve_title(self, mx: int, my: int) -> tuple[str, str]:

        resolver = getattr(self._window, '_hover_name_resolver', None)
        if resolver is not None:
            try:
                name = resolver(mx, my)
            except Exception:
                logger.exception('Hover name resolver error')
                name = None
            if name:
                return 'Region', str(name)
        providers = getattr(self._window, '_context_menu_targets', ()) or ()
        for provider in providers:
            try:
                spec = provider(mx, my)
            except Exception:
                logger.exception('Hover name provider error')
                spec = None
            if spec is not None:
                return 'Object', str(spec[0])
        return '', ''

    def _move(self, event) -> bool:
        pos = event.position()
        kind, title = self._resolve_title(int(pos.x()), int(pos.y()))
        if title == self._last:
            return False
        self._last = title
        if title:
            overlay_event(logger, f'{kind}({title})', 'Hover')
        win = self._window

        wrapped = keep_case(title) if title else ''
        win._hover_overlay = wrapped
        fallback = getattr(win, '_message_overlay', '') or None
        win._widget.set_message_overlay(wrapped or fallback)
        request_repaint(win)
        return False

    def handle(self, kind: str, event) -> bool:
        if kind == 'move':
            return self._move(event)
        return False

def register_hover_name(window) -> HoverNameMouseHandler:
    handler = HoverNameMouseHandler(window)
    handler.attach()
    logger.info('Hover name overlay attached: object/region under cursor')
    return handler
