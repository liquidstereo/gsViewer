import logging
from pathlib import Path

from process.common.widget import request_repaint
from process.transform.attr_overlay import reset_attr_overlay_if_idle
from process.component.region_volume.keys import show_message_overlay
from process.component.region_volume.registry import get_registry, renumber_box_labels
from process.component.region_volume.settings import REGION_DUPLICATE_OFFSET_RATIO

logger = logging.getLogger(__name__)

def _delete_region_json(ctrl) -> None:
    for attr in ('region_path', 'keyframes_path', 'curves_path'):
        path = getattr(ctrl, attr, None)
        if path is None:
            continue
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as e:
            logger.warning('Region JSON remove failed (%s): %s', attr, e)

def _repoint_channel(window, ctrl) -> None:
    channel = getattr(ctrl, '_channel', None)
    if channel is None:
        return
    if getattr(window, channel, None) is not ctrl:
        return
    sibling = next(
        (m for m in get_registry(window).members
         if getattr(m, '_channel', None) == channel),
        None,
    )
    setattr(window, channel, sibling)

def _resave_region_json(ctrl) -> None:
    try:
        ctrl.save_region()
        if ctrl.keyframes.count() > 0:
            ctrl.keyframes.save(ctrl.keyframes_path)
        ctrl.save_curves()
    except (OSError, AttributeError) as e:
        logger.warning('Region JSON restore failed: %s', e)

def delete_selected(window) -> bool:
    reg = get_registry(window)
    if not reg.user_selected:
        return False
    ctrl = reg.selected()
    if ctrl is None:
        return False
    index = reg.index_of(ctrl)
    palette = reg.palettes[index] if 0 <= index < len(reg.palettes) else None
    channel = getattr(ctrl, '_channel', None)
    was_holder = (channel is not None
                  and getattr(window, channel, None) is ctrl)
    label = getattr(ctrl, 'overlay_label', '') or 'REGION'
    base = getattr(ctrl, '_base_label', None)

    def _do_delete() -> None:
        reg2 = get_registry(window)
        if not reg2.unregister(ctrl):
            return
        _repoint_channel(window, ctrl)
        _delete_region_json(ctrl)
        renumber_box_labels(window, base)
        reset_attr_overlay_if_idle(window)
        request_repaint(window)

    def _do_restore() -> None:
        reg2 = get_registry(window)
        if ctrl in reg2.members:
            return
        reg2.reinsert(ctrl, palette, index)
        renumber_box_labels(window, base)
        reg2.selected_index = reg2.index_of(ctrl)
        reg2.user_selected = True
        if was_holder and channel is not None:
            setattr(window, channel, ctrl)
        _resave_region_json(ctrl)
        request_repaint(window)

    _do_delete()
    show_message_overlay(window, f'DELETED: {label}')
    logger.info('RegionVolume deleted: %s', label)
    stack = getattr(window, '_undo_stack', None)
    if stack is not None:
        stack.push(f'Delete {label}', _do_restore, _do_delete)
    return True

def _copy_region_transform(src, dst) -> None:
    dst.center = src.center.copy()
    dst.size = src.size.copy()
    dst.rotation = src.rotation.copy()
    dst.softness = float(src.softness)

def _copy_effect_state(sel, new) -> None:
    src = getattr(sel, 'system', None)
    dst = getattr(new, 'system', None)
    if src is not None and dst is not None:
        for key, value in vars(src).items():
            if key == 'region' or key.startswith('_'):
                continue
            if isinstance(value, (bool, int, float, str, tuple)):
                setattr(dst, key, value)
    dump = getattr(sel, 'curve_state', None)
    load = getattr(new, 'apply_curve_state', None)
    if callable(dump) and callable(load):
        load(dump())

def duplicate_selected(window) -> bool:
    reg = get_registry(window)
    if not reg.user_selected:
        return False
    sel = reg.selected()
    if sel is None:
        return False
    new = type(sel)()
    new.attach(window)
    if new.shape != sel.shape:
        new.rebuild_region(sel.shape)
    _copy_region_transform(sel.region, new.region)
    _copy_effect_state(sel, new)
    new.region.center[0] += float(sel.region.size[0]) *\
        REGION_DUPLICATE_OFFSET_RATIO
    new.on_select()
    label = getattr(new, 'overlay_label', '') or 'REGION'
    show_message_overlay(window, f'DUPLICATED: {label}')
    logger.info('RegionVolume duplicated: %s', label)
    request_repaint(window)
    return True
