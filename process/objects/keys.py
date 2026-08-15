import logging
from collections.abc import Callable

from process.undo import record_object_state, snapshot_object_state

logger = logging.getLogger(__name__)

def _render(win) -> None:
    render = getattr(win, '_render_current', None)
    if render is not None:
        render()

def _set_seq(win, input_id: str | None) -> None:
    fn = getattr(win, 'set_active_seq_input', None)
    if fn is not None:
        fn(input_id)

def _toggle_single_select(win, controller, target_id: str) -> None:
    if controller.selected_id == target_id:
        controller.select(None)
        _set_seq(win, getattr(win, '_active_id', None))
        logger.info('Object deselected: %s', target_id)
    else:
        controller.select(target_id)
        _set_seq(win, target_id)
        logger.info('Object selected: %s', target_id)
    _render(win)

def isolate_object(win, index: int) -> None:
    ids = win.input_ids()
    if not ids or not (0 <= index < len(ids)):
        return
    controller = getattr(win, '_input_transform', None)
    if controller is None:
        return

    if getattr(controller, 'solo_id', None) is not None:
        controller.select(ids[index])
        _render(win)
        return
    target_id = ids[index]
    others = [iid for iid in ids if iid != target_id]
    if not others:
        _toggle_single_select(win, controller, target_id)
        return
    before = snapshot_object_state(win, controller)
    is_soloed = (
        target_id not in controller.isolate_hidden
        and all(o in controller.isolate_hidden for o in others)
    )
    if is_soloed:
        controller.isolate_hidden = set()
        controller.select(None)
        _set_seq(win, getattr(win, '_active_id', None))
        logger.info('Object isolate cleared (show all)')
    else:
        controller.isolate_hidden = set(others)
        controller.select(target_id)
        _set_seq(win, target_id)
        logger.info('Object isolated: %s', target_id)
    _render(win)
    record_object_state(
        win, controller, before,
        snapshot_object_state(win, controller), 'Isolate',
    )

def make_isolate_handler(index: int) -> Callable:
    def _handle(win) -> None:
        isolate_object(win, index)
    return _handle
