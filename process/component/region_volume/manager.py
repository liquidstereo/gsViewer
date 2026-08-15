import logging

from process.common import lock_hide_suffix
from process.common.widget import request_repaint
from process.transform.attr_overlay import reset_attr_overlay_if_idle
from process.widget.overlays.region_list import register_region_entry_source
from process.component.region_volume.context_menu import register_region_context
from process.component.region_volume.controller import RegionVolumeBoxController
from process.component.region_volume.manager_keys import register_keys
from process.component.region_volume.manager_paint import (
    register_controller, _register_keyframes_marker_painter,
    _register_label_painter, _register_region_painter,
)
from process.component.region_volume.registry import get_registry
from process.component.region_volume.solo import (
    has_region_solo_target, toggle_region_solo,
)
from process.component.region_volume.lifecycle import delete_selected, duplicate_selected
from process.component.region_volume.keyframe_animation import RegionVolumeKeyframeAnimator
from process.component.region_volume.hover_select import hover_winner
from process.component.region_volume.mouse import RegionVolumeMouseHandler
from process.component.region_volume.overlay import RegionPalette
from process.component.region_volume.paint import RegionVolumePalette
from process.component.region_volume.polygon import register_polygon_drawing

logger = logging.getLogger(__name__)

def _region_list_items(window) -> list:
    reg = get_registry(window)
    items = []
    for ctrl in reg.members:
        label = getattr(ctrl, 'overlay_label', '') or 'REGION'
        vis = getattr(ctrl, 'is_visible', None)
        visible = bool(vis()) if callable(vis) else True
        lock_fn = getattr(ctrl, 'is_region_locked', None)
        locked = bool(lock_fn()) if callable(lock_fn) else False
        suffix = lock_hide_suffix(not visible, locked)
        if reg.is_soloed(ctrl):
            suffix = f'{suffix} (Solo)'
        items.append((
            label, reg.is_active_selection(ctrl), visible, suffix,
        ))
    return items

def _region_select(window, index: int) -> None:
    reg = get_registry(window)
    if not (0 <= index < len(reg.members)):
        return
    member = reg.members[index]

    if reg.is_active_selection(member):
        reg.user_selected = False
        reset_attr_overlay_if_idle(window)
    else:
        member.on_select()
    request_repaint(window)

def _hover_region_name(window, mx: int, my: int) -> str | None:
    reg = get_registry(window)
    if not reg.members:
        return None
    winner = hover_winner(reg.members)
    if winner is None:
        return None
    return getattr(winner, 'overlay_label', '') or 'REGION'

def _register_region_list_channel(window) -> None:
    if getattr(window, '_region_volume_list_registered', False):
        return
    window._region_volume_list_registered = True
    register_region_entry_source(
        window,
        lambda: _region_list_items(window),
        lambda i: _region_select(window, i),
    )
    window._hover_name_resolver = lambda mx, my: _hover_region_name(
        window, mx, my)

    window._region_solo_toggle = lambda: (
        toggle_region_solo(window)
        if has_region_solo_target(window) else False
    )

    window._region_delete_cb = lambda: delete_selected(window)
    window._region_duplicate_cb = lambda: duplicate_selected(window)

    providers = getattr(window, '_delete_providers', None)
    if providers is not None:
        providers.append(lambda: _region_delete_target(window))
    _register_region_preview_hook(window)

def _region_delete_target(window):
    reg = get_registry(window)
    if not reg.user_selected:
        return None
    ctrl = reg.selected()
    if ctrl is None:
        return None
    label = getattr(ctrl, 'overlay_label', '') or 'REGION'
    return (label, lambda: delete_selected(window))

def _register_region_preview_hook(window) -> None:
    hooks = getattr(window, '_preview_hooks', None)
    if hooks is None:
        return
    saved: dict = {}

    def hook(compact: bool) -> None:
        for ctrl in get_registry(window).members:
            if compact:
                saved.setdefault(id(ctrl), ctrl.region_visible)
                ctrl.region_visible = False
            elif id(ctrl) in saved:
                ctrl.region_visible = saved.pop(id(ctrl))

    hooks.append(hook)

def register_box_controller(
    window, plugin: RegionVolumeBoxController,
    palette: RegionVolumePalette | None = None,
    region_palette: RegionPalette | None = None,
    with_keyframes: bool = True,
    region_painter_override=None,
    shape: str = 'cube',
) -> RegionVolumeMouseHandler:
    plugin._window = window
    plugin.shape = shape

    plugin._default_shape = shape
    plugin.init_paths(window)
    get_registry(window).register(plugin, region_palette)
    _register_region_list_channel(window)
    if with_keyframes:
        plugin.keyframe_animator = RegionVolumeKeyframeAnimator(window, plugin)
    mouse = register_controller(window, plugin, palette)
    _register_region_painter(
        window, plugin, region_palette, region_painter_override,
    )
    _register_label_painter(window, plugin)
    if with_keyframes:
        _register_keyframes_marker_painter(window, plugin, region_palette)
    register_keys(window, plugin, with_keyframes)
    register_region_context(window, plugin)
    register_polygon_drawing(window, plugin)
    _register_corner_bracket_toggle(window)
    return mouse

def _register_corner_bracket_toggle(window) -> None:
    def _toggle() -> bool:
        reg = get_registry(window)
        if not getattr(reg, 'user_selected', False):
            return False
        ctrl = reg.selected()
        if ctrl is None:
            return False
        ctrl.bracket_mode = not getattr(ctrl, 'bracket_mode', False)
        return True

    window._corner_bracket_region_toggle = _toggle
