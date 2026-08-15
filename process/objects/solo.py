import logging

from process.common import display_name
from process.handle import set_message_overlay

logger = logging.getLogger(__name__)

def _render(win) -> None:
    render = getattr(win, '_render_current', None)
    if render is not None:
        render()

def _set_seq(win, input_id: str | None) -> None:
    fn = getattr(win, 'set_active_seq_input', None)
    if fn is not None:
        fn(input_id)

def _clear_object_solo(win, controller) -> None:
    controller.solo_id = None
    controller.solo_owner_name = None
    controller.isolate_hidden = set()
    set_message_overlay(win, '')
    _set_seq(win, getattr(win, '_active_id', None))
    _render(win)
    logger.info('Object solo cleared')

def _activate_object_solo(win, controller, target_id: str) -> bool:
    ids = win.input_ids()
    if target_id not in ids:
        return False
    others = [iid for iid in ids if iid != target_id]
    name = display_name(win, target_id)
    controller.solo_id = target_id
    controller.solo_owner_name = name
    controller.isolate_hidden = set(others)
    controller.select(target_id)
    set_message_overlay(win, f'SOLO: {name}')
    _set_seq(win, target_id)
    _render(win)
    logger.info('Object solo: %s', target_id)
    return True

def toggle_object_solo(win, target_id: str | None = None) -> bool:
    controller = getattr(win, '_input_transform', None)
    if controller is None:
        return False
    tid = target_id if target_id is not None else controller.selected_id
    if controller.solo_id is not None and (
            tid is None or tid == controller.solo_id):
        _clear_object_solo(win, controller)
        return True
    if tid is None:
        return False
    return _activate_object_solo(win, controller, tid)

def handle_solo(win) -> None:
    hook = getattr(win, '_region_solo_toggle', None)
    if callable(hook) and hook():
        return
    toggle_object_solo(win)
