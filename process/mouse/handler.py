import logging

from PySide6.QtCore import Qt

import process.mouse.input as mouse_input

logger = logging.getLogger(__name__)

def on_cam_event(win, kind: str, event) -> None:
    if kind == 'press':
        win._drag_pos = event.position().toPoint()
        win._drag_btn = event.button()
    elif kind == 'release':
        win._drag_pos = None
        win._drag_btn = None
    elif kind == 'move' and win._drag_pos is not None:
        cur = event.position().toPoint()
        dx = cur.x() - win._drag_pos.x()
        dy = cur.y() - win._drag_pos.y()
        win._drag_pos = cur
        if win._drag_btn == Qt.MouseButton.LeftButton:
            mouse_input.orbit(win, dx, dy)
        elif win._drag_btn in (
            Qt.MouseButton.RightButton,
            Qt.MouseButton.MiddleButton,
        ):
            mouse_input.pan(win, dx, dy)
    elif kind == 'wheel':
        steps = event.angleDelta().y() / 120.0
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            mouse_input.zoom_fov(win, steps)
        else:
            mouse_input.zoom(win, steps)
