import logging

import numpy as np

from process.common import request_repaint

logger = logging.getLogger(__name__)

def snapshot_transform(obj) -> dict:
    return {
        'center': np.asarray(obj.center).copy(),
        'size': np.asarray(obj.size).copy(),
        'rotation': np.asarray(obj.rotation).copy(),
    }

def _transform_changed(a: dict, b: dict) -> bool:
    return not (
        np.allclose(a['center'], b['center'])
        and np.allclose(a['size'], b['size'])
        and np.allclose(a['rotation'], b['rotation'])
    )

def _apply_transform(obj, snap: dict) -> None:
    obj.center = snap['center'].copy()
    obj.size = snap['size'].copy()
    obj.rotation = snap['rotation'].copy()

def record_transform(
    window, ctrl, input_id: str, before: dict, after: dict,
) -> None:
    stack = getattr(window, '_undo_stack', None)
    if stack is None or not _transform_changed(before, after):
        return

    def restore(snap: dict) -> None:
        target = ctrl.targets.get(input_id)
        if target is None:
            return
        _apply_transform(target, snap)
        ctrl.on_change()

    stack.push(
        'Object transform',
        lambda: restore(before), lambda: restore(after),
    )

def record_region(window, ctrl, before: dict, after: dict) -> None:
    stack = getattr(window, '_undo_stack', None)
    if stack is None or not _transform_changed(before, after):
        return

    def restore(snap: dict) -> None:
        region = getattr(ctrl, 'region', None)
        if region is None:
            return
        _apply_transform(region, snap)
        ctrl.on_change()
        save = getattr(ctrl, 'save_region', None)
        if callable(save):
            save()

    stack.push(
        'Region transform',
        lambda: restore(before), lambda: restore(after),
    )

def snapshot_region_state(ctrl) -> dict:
    return {
        'visible': bool(getattr(ctrl, 'region_visible', False)),
        'locked': bool(getattr(ctrl, 'region_locked', False)),
    }

def _region_state_changed(a: dict, b: dict) -> bool:
    return a['visible'] != b['visible'] or a['locked'] != b['locked']

def record_region_state(
    window, ctrl, before: dict, after: dict, label: str = 'Region state',
) -> None:
    stack = getattr(window, '_undo_stack', None)
    if stack is None or not _region_state_changed(before, after):
        return

    def restore(snap: dict) -> None:
        ctrl.region_visible = snap['visible']
        ctrl.region_locked = snap['locked']
        request_repaint(window)

    stack.push(label, lambda: restore(before), lambda: restore(after))

def record_attr(
    window, rows_getter, label: str, before, after,
) -> None:
    stack = getattr(window, '_undo_stack', None)
    if stack is None or before == after:
        return

    def restore(value) -> None:
        row = next(
            (r for r in rows_getter() if r.spec.label == label), None,
        )
        if row is None:
            return
        spec = row.spec
        if spec.set is not None:
            spec.set(value)
        if spec.on_commit is not None:
            spec.on_commit()
        for cb in getattr(window, '_attr_commit_listeners', []):
            cb(row)
        request_repaint(window)

    stack.push(
        f'Attr {label}',
        lambda: restore(before), lambda: restore(after),
    )

def record_keyframe_seq(
    window, store, seq, before: tuple, after: tuple,
    label: str = 'Object keyframe',
) -> None:
    stack = getattr(window, '_undo_stack', None)
    if stack is None:
        return
    if len(before[0]) == len(after[0]) and before[1] == after[1]:
        return

    def restore(snap: tuple) -> None:
        seq.restore(snap)
        store.save()
        request_repaint(window)

    stack.push(label, lambda: restore(before), lambda: restore(after))

def snapshot_object_state(window, ctrl) -> dict:
    return {
        'hidden': set(ctrl.hidden),
        'isolate_hidden': set(getattr(ctrl, 'isolate_hidden', set())),
        'locked': set(ctrl.locked),
        'point_scale': dict(ctrl.point_scale),
        'selected_id': ctrl.selected_id,
        'scale_mult': getattr(window, '_scale_mult', None),
    }

def _object_state_changed(a: dict, b: dict) -> bool:
    return (
        a['hidden'] != b['hidden']
        or a.get('isolate_hidden') != b.get('isolate_hidden')
        or a['locked'] != b['locked']
        or a['point_scale'] != b['point_scale']
        or a['scale_mult'] != b['scale_mult']
    )

def _resync_seq(window, ctrl) -> None:
    fn = getattr(window, 'set_active_seq_input', None)
    if fn is None:
        return
    sid = ctrl.selected_id
    fn(sid if sid is not None else getattr(window, '_active_id', None))

def record_object_state(
    window, ctrl, before: dict, after: dict, label: str = 'Object state',
) -> None:
    if not _object_state_changed(before, after):
        return
    from process.transform.attr_persist import save_object_attrs
    save_object_attrs(ctrl)
    stack = getattr(window, '_undo_stack', None)
    if stack is None:
        return

    def restore(snap: dict) -> None:
        ctrl.hidden = set(snap['hidden'])
        ctrl.isolate_hidden = set(snap.get('isolate_hidden', set()))
        ctrl.locked = set(snap['locked'])
        ctrl.point_scale = dict(snap['point_scale'])
        ctrl.selected_id = snap['selected_id']
        if snap['scale_mult'] is not None:
            window._scale_mult = snap['scale_mult']
        ctrl.on_change()
        _resync_seq(window, ctrl)
        save_object_attrs(ctrl)

    stack.push(label, lambda: restore(before), lambda: restore(after))
