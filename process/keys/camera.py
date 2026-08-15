import copy
import logging
import math

logger = logging.getLogger(__name__)

_ORTHO_VIEWS: dict[str, tuple[float, float]] = {
    'FRONT':  (0.0,            0.0),
    'BACK':   (math.pi,        0.0),
    'LEFT':   (math.pi / 2,    0.0),
    'RIGHT':  (-math.pi / 2,   0.0),
    'TOP':    (0.0,            math.pi / 2),
    'BOTTOM': (0.0,           -math.pi / 2),
}

def _restore_perspective(win) -> None:
    if win._ortho_saved is None:
        win._ortho_active = None
        return
    win._cam = win._ortho_saved
    win._ortho_saved = None
    win._ortho_active = None
    win._message_overlay = 'VIEW: PERSPECTIVE'
    win._message_overlay_timer.start()
    win._update_cam()
    logger.info('Camera restored to perspective')

def _set_ortho_view(win, name: str) -> None:

    if win._ortho_active == name:
        _restore_perspective(win)
        return

    if win._ortho_active is None:
        win._ortho_saved = copy.deepcopy(win._cam)
    az, el = _ORTHO_VIEWS[name]
    win._cam['azimuth'] = az
    win._cam['elevation'] = el
    win._ortho_active = name
    win._message_overlay = f'ORTHO: {name}'
    win._message_overlay_timer.start()
    win._update_cam()
    logger.info('Ortho view: %s', name)

def handle_ortho_front(win) -> None:
    _set_ortho_view(win, 'FRONT')

def handle_ortho_back(win) -> None:
    _set_ortho_view(win, 'BACK')

def handle_ortho_left(win) -> None:
    _set_ortho_view(win, 'LEFT')

def handle_ortho_right(win) -> None:
    _set_ortho_view(win, 'RIGHT')

def handle_ortho_top(win) -> None:
    _set_ortho_view(win, 'TOP')

def handle_ortho_bottom(win) -> None:
    _set_ortho_view(win, 'BOTTOM')

def handle_reset_camera(win) -> None:
    win._cam = copy.deepcopy(win._init_cam)
    win._ortho_active = None
    win._ortho_saved = None
    win._annot_cursor = -1
    win._update_cam()
    logger.info('Camera reset to initial state')
