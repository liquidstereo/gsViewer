def has_active_selection(window) -> bool:
    itc = getattr(window, '_input_transform', None)
    if itc is not None and getattr(itc, 'selected_id', None) is not None:
        return True
    reg = getattr(window, '_region_volume_registry', None)
    if reg is not None and getattr(reg, 'user_selected', False):
        return True
    return False

def attr_solo_active(window, owner: str | None = None) -> bool:
    if has_active_selection(window):
        return False
    for flag in getattr(window, '_attr_solo_flags', ()):
        if flag == owner:
            continue
        if getattr(window, flag, False):
            return True
    return False

def register_solo_flag(window, flag: str) -> None:
    flags = getattr(window, '_attr_solo_flags', None)
    if flags is None:
        flags = []
        window._attr_solo_flags = flags
    if flag not in flags:
        flags.append(flag)

def activate_solo_selection(window, owner: str) -> None:
    for flag in getattr(window, '_attr_solo_flags', ()):
        if flag != owner:
            setattr(window, flag, False)
    itc = getattr(window, '_input_transform', None)
    if itc is not None:
        itc.select(None)
    reg = getattr(window, '_region_volume_registry', None)
    if reg is not None:
        reg.user_selected = False

def close_attr_editor_panel(window) -> bool:
    widget = getattr(window, '_widget', None)
    if widget is None or getattr(widget, '_attr_overlay_hidden', False):
        return False
    if not has_active_selection(window):
        return False
    widget._attr_overlay_hidden = True
    widget.update()
    return True

def reset_attr_overlay_if_idle(window) -> None:
    if has_active_selection(window):
        return

    for flag in getattr(window, '_attr_solo_flags', ()):
        setattr(window, flag, False)
    widget = getattr(window, '_widget', None)
    if widget is not None:
        widget._attr_overlay_hidden = True
        widget.update()

def deselect_all(window) -> None:
    itc = getattr(window, '_input_transform', None)
    if itc is not None:
        itc.select(None)
    reg = getattr(window, '_region_volume_registry', None)
    if reg is not None:
        reg.user_selected = False
    for flag in getattr(window, '_attr_solo_flags', ()):
        setattr(window, flag, False)
    widget = getattr(window, '_widget', None)
    if widget is not None:
        widget._attr_overlay_hidden = True
        widget.update()
