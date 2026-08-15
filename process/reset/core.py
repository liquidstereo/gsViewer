import logging
import shutil

from process.common import json_root_path
from process.common.attr_random import reset_window_attr_random
from process.keys.home import handle_home_reset

logger = logging.getLogger(__name__)

def _delete_session_json(win) -> None:
    key = getattr(win, '_json_key', None)
    if not key:
        return
    root = json_root_path(key, '_').parent
    if not root.is_dir():
        return
    try:
        shutil.rmtree(root)
        logger.info('Session json removed: %s', root.name)
    except OSError:
        logger.exception('Session json delete failed: %s', root)

def _reset_object_attrs(win) -> None:
    controller = getattr(win, '_input_transform', None)
    if controller is None:
        return
    controller.hidden.clear()
    controller.isolate_hidden.clear()
    controller.solo_id = None
    controller.solo_owner_name = None
    controller.point_scale.clear()
    controller.bracket_mode.clear()
    controller._saved_attrs = {}
    controller._last_hidden = None

def _reset_keyframes(win) -> None:
    for attr in ('_object_keyframes', '_global_keyframes'):
        store = getattr(win, attr, None)
        if store is None:
            continue
        animator = getattr(store, 'animator', None)
        if animator is not None:
            animator.stop()
        clear = getattr(store, 'clear', None)
        if callable(clear):
            clear()

def reset_all(win) -> None:
    _delete_session_json(win)
    _reset_object_attrs(win)
    _reset_keyframes(win)
    reset_window_attr_random(win)
    handle_home_reset(win)
    logger.info('Reset all completed')
