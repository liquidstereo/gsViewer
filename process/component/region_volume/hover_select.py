def region_member_dragging(ctrl) -> bool:
    mh = getattr(ctrl, '_region_mouse', None)
    fn = getattr(mh, 'is_dragging', None)
    return bool(callable(fn) and fn())

def region_member_hovered(ctrl) -> bool:
    mh = getattr(ctrl, '_region_mouse', None)
    if mh is None:
        return False
    if getattr(mh, 'hover', None) is not None:
        return True
    if getattr(mh, 'hover_body', False):
        return True
    return region_member_dragging(ctrl)

def region_member_volume(ctrl) -> float:
    region = getattr(ctrl, 'region', None)
    size = getattr(region, 'size', None)
    if size is None or len(size) < 3:
        return float('inf')
    return float(abs(size[0] * size[1] * size[2]))

def hover_winner(members):
    dragging = [m for m in members if region_member_dragging(m)]
    if dragging:
        return min(dragging, key=region_member_volume)
    hovered = [m for m in members if region_member_hovered(m)]
    if not hovered:
        return None
    return min(hovered, key=region_member_volume)

def region_is_selected(plugin) -> bool:
    if getattr(plugin, 'region_locked', False):
        return False
    win = getattr(plugin, '_window', None)
    reg = getattr(win, '_region_volume_registry', None)

    fn = getattr(reg, 'is_active_selection', None)
    if callable(fn) and fn(plugin):
        return True
    if not region_member_hovered(plugin):
        return False
    members = getattr(reg, 'members', None)
    if not members or len(members) <= 1:
        return True
    return hover_winner(members) is plugin
