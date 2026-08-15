import logging

from process.handle import set_message_overlay

logger = logging.getLogger(__name__)

def _render(win) -> None:
    render = getattr(win, '_render_current', None)
    if render is not None:
        render()
    elif hasattr(win, '_widget'):
        win._widget.update()

def _clear_region_solo(win, reg) -> None:
    for ctrl, vis in reg._solo_saved_vis.items():
        ctrl.region_visible = vis
    reg._solo_saved_vis = {}
    reg.solo_index = -1
    itc = getattr(win, '_input_transform', None)
    if itc is not None:
        itc.solo_owner_name = None
    set_message_overlay(win, '')
    _render(win)
    logger.info('Region solo cleared')

def _activate_region_solo(win, reg, ctrl) -> bool:
    idx = reg.index_of(ctrl)
    if idx < 0:
        return False
    reg._solo_saved_vis = {
        m: m.region_visible for m in reg.members if m is not ctrl
    }
    for m in reg.members:
        if m is not ctrl:
            m.region_visible = False
    ctrl.region_visible = True
    reg.solo_index = idx
    label = getattr(ctrl, 'overlay_label', '') or 'REGION'
    itc = getattr(win, '_input_transform', None)
    if itc is not None:
        itc.solo_owner_name = label
    ctrl.on_select()
    set_message_overlay(win, f'SOLO: {label}')
    _render(win)
    logger.info('Region solo: %s', label)
    return True

def toggle_region_solo(win, ctrl=None) -> bool:
    reg = getattr(win, '_region_volume_registry', None)
    if reg is None:
        return False
    target = ctrl if ctrl is not None else reg.solo_member()
    if target is None and reg.user_selected:
        target = reg.selected()
    if reg.solo_active() and (target is None or reg.is_soloed(target)):
        _clear_region_solo(win, reg)
        return True
    if target is None:
        return False
    return _activate_region_solo(win, reg, target)

def clear_region_solo(win) -> None:
    reg = getattr(win, '_region_volume_registry', None)
    if reg is not None and reg.solo_active():
        _clear_region_solo(win, reg)

def has_region_solo_target(win) -> bool:

    itc = getattr(win, '_input_transform', None)
    if itc is not None and getattr(itc, 'solo_id', None) is not None:
        return False
    reg = getattr(win, '_region_volume_registry', None)
    if reg is None:
        return False
    return reg.solo_active() or bool(reg.user_selected and reg.selected())
