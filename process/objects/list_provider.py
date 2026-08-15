from process.common import display_name, lock_hide_suffix
from process.widget.text_case import keep_case

def _point_count(controller, input_id: str) -> int:
    if controller is None:
        return 0
    target = controller.targets.get(input_id)
    if target is None:
        target = controller.targets.get('__primary__')
    return int(getattr(target, 'point_count', 0)) if target is not None else 0

def _file_count(win, input_id: str) -> int:
    inputs = getattr(win, '_inputs', None)
    if not inputs or input_id not in inputs:
        return 0
    return len(inputs[input_id].get('files', ()))

def _build_chain_object_list(win, segs: list) -> list:

    active = getattr(win, '_chain_active_iid', None)
    items: list = []
    for iid, _start, length in segs:
        name = keep_case(display_name(win, iid))
        items.append((
            name, iid == active, True, 0, length, '', False, False,
        ))
    return items

def build_object_list(win) -> list:
    segs = getattr(win, '_chain_segments', None)
    if segs:
        return _build_chain_object_list(win, segs)
    ids = win.input_ids()
    if not ids:
        return []
    controller = getattr(win, '_input_transform', None)
    items: list = []
    for iid in ids:
        name = keep_case(display_name(win, iid))
        selected = bool(
            controller is not None and controller.selected_id == iid
        )
        visible = not bool(
            controller is not None and controller.is_hidden(iid)
        )
        locked = bool(
            controller is not None and controller.is_locked(iid)
        )
        manual_hidden = bool(
            controller is not None and iid in controller.hidden
        )
        solo = bool(
            controller is not None and controller.solo_id == iid
        )
        items.append((
            name, selected, visible,
            _point_count(controller, iid), _file_count(win, iid),
            lock_hide_suffix(not visible, locked), manual_hidden, solo,
        ))
    return items
