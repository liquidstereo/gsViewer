import logging

from process.common import request_repaint

logger = logging.getLogger(__name__)

def _show(win, text: str) -> None:
    win._message_overlay = text
    timer = getattr(win, '_message_overlay_timer', None)
    if timer is not None:
        timer.start()
    request_repaint(win)

def handle_undo(win) -> None:
    stack = getattr(win, '_undo_stack', None)
    if stack is None:
        return
    label = stack.undo()
    logger.info('Undo: %s', label or '(empty)')
    _show(win, f'UNDO: {label}' if label else 'NOTHING TO UNDO')

def handle_redo(win) -> None:
    stack = getattr(win, '_undo_stack', None)
    if stack is None:
        return
    label = stack.redo()
    logger.info('Redo: %s', label or '(empty)')
    _show(win, f'REDO: {label}' if label else 'NOTHING TO REDO')
