import logging

import numpy as np

from process.overlay_coord import region_gizmo_axes
from configs.settings_color import LOCKED_COLOR
from configs.settings_style import (
    REGION_CORNER_BRACKETS, SELECTED_COLOR, STARTUP_REGION_CORNER_BRACKETS,
)
from process.transform.paint import paint_selection_box
from process.component.region_volume.handles import region_volume_world_length
from process.component.region_volume.label import paint_region_label
from process.component.region_volume.registry import get_registry
from process.component.region_volume.markers import compute_region_volume_keyframe_markers
from process.component.region_volume.mouse import (
    RegionVolumeController, RegionVolumeMouseHandler,
)
from process.component.region_volume.hover_select import region_is_selected
from process.component.region_volume.overlay import (
    RegionPalette, compute_region_segments,
    resolve_palette, paint_region, paint_region_faces,
)
from process.component.region_volume.overlay_capsule import make_capsule_painter
from process.component.region_volume.overlay_cone import make_cone_painter
from process.component.region_volume.overlay_cylinder import make_cylinder_painter
from process.component.region_volume.overlay_sphere import make_sphere_painter
from process.component.region_volume.overlay_torus import make_torus_painter
from process.component.region_volume.polygon import make_polygon_painter
from process.component.region_volume.paint import (
    RegionVolumePalette, paint_translate_region_volume,
)
from process.component.region_volume.paint_handles import (
    paint_region_volume_shift_indicator, paint_rotate_region_volume,
    paint_scale_region_volume,
)
from process.component.region_volume.paint_markers import paint_region_volume_keyframes
from process.component.region_volume.settings import (
    REGION_VOLUME_SCREEN_LEN_PX, TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
)

logger = logging.getLogger(__name__)

def _is_registered(window, ctrl) -> bool:
    return ctrl in get_registry(window).members

class _ControllerBinding:

    __slots__ = ('controller', 'mouse', 'palette')

    def __init__(
        self, controller: RegionVolumeController,
        mouse: RegionVolumeMouseHandler, palette: RegionVolumePalette | None,
    ) -> None:
        self.controller = controller
        self.mouse = mouse
        self.palette = palette

def register_controller(
    window, controller: RegionVolumeController,
    palette: RegionVolumePalette | None = None,
) -> RegionVolumeMouseHandler:
    mouse = RegionVolumeMouseHandler(controller)

    controller._region_mouse = mouse
    if hasattr(window, '_mouse_handlers'):
        mouse.attach(window)
    binding = _ControllerBinding(controller, mouse, palette)
    painter_fn = _make_overlay_painter(window, binding)
    if hasattr(window, '_widget'):
        ovs = getattr(window._widget, '_underlay_painters', None)
        if ovs is not None:
            ovs.append(painter_fn)
    _register_status_provider(window, controller)
    logger.info('RegionVolume controller registered')
    return mouse

def _make_status_provider(window, controller: RegionVolumeController):
    def provider() -> dict | None:
        if not get_registry(window).is_active_selection(controller):
            return None
        target = controller.target
        if target is None:
            return None
        base_size = getattr(target, '_default_size', None)
        if base_size is None:
            base_size = getattr(target, 'size', None)
        base_rot = getattr(target, '_default_rotation', None)
        if base_rot is None:
            base_rot = np.eye(3, dtype=np.float32)
        label = getattr(controller, 'overlay_label', '') or 'REGION'
        lock_fn = getattr(controller, 'is_region_locked', None)
        locked = bool(lock_fn()) if callable(lock_fn) else None
        return {
            'label': label,
            'center': np.asarray(target.center, dtype=np.float32),
            'size': np.asarray(target.size, dtype=np.float32),
            'base_size': np.asarray(base_size, dtype=np.float32),
            'rotation': np.asarray(target.rotation, dtype=np.float32),
            'base_rotation': np.asarray(base_rot, dtype=np.float32),
            'count': None,
            'lock': locked,
            'solo': get_registry(window).is_soloed(controller),
        }
    return provider

def _register_status_provider(
    window, controller: RegionVolumeController,
) -> None:
    providers = getattr(window, '_status_providers', None)
    if providers is None:
        providers = []
        window._status_providers = providers
    providers.append(_make_status_provider(window, controller))

def _make_cube_painter(window, plugin, region_palette):
    palette = region_palette

    def _paint(painter, w: int, h: int, depth) -> None:
        if not plugin.region_visible:
            return
        locked = getattr(plugin, 'region_locked', False)
        selected = region_is_selected(plugin)
        sel_member = get_registry(window).is_selected(plugin)
        pal = resolve_palette(palette, locked, selected)

        paint_region_faces(
            painter, window, plugin.region,
            selected=(selected or sel_member), palette=pal,
        )
        segs = compute_region_segments(window, plugin.region)
        paint_region(
            painter, segs, depth, w, h,
            win=window, region=plugin.region,
            bold=(selected or sel_member), palette=pal,
        )
    return _paint

def _register_region_painter(
    window, plugin, region_palette, cube_override,
) -> None:
    if not hasattr(window, '_widget'):
        return
    ovs = getattr(window._widget, '_underlay_painters', None)
    if ovs is None:
        return
    cube_p = cube_override or _make_cube_painter(window, plugin, region_palette)
    painters = {
        'sphere': make_sphere_painter(plugin, window, region_palette),
        'cylinder': make_cylinder_painter(plugin, window, region_palette),
        'cone': make_cone_painter(plugin, window, region_palette),
        'capsule': make_capsule_painter(plugin, window, region_palette),
        'torus': make_torus_painter(plugin, window, region_palette),
        'polygon': make_polygon_painter(plugin, window, region_palette),
    }

    def _paint(painter, w: int, h: int, depth) -> None:
        if not _is_registered(window, plugin):
            return
        if not plugin.region_visible:
            _paint_hidden_hover_brackets(painter, window, plugin)
            return

        if getattr(plugin, 'bracket_mode', False):
            _paint_region_brackets(painter, window, plugin)
            return
        fn = painters.get(getattr(plugin, 'shape', 'cube'), cube_p)
        fn(painter, w, h, depth)
    ovs.append(_paint)

def _paint_region_brackets(painter, window, plugin) -> None:
    region = getattr(plugin, 'region', None)
    edges_fn = getattr(region, 'edges', None)
    if not callable(edges_fn):
        return
    paint_selection_box(painter, window, edges_fn(), color_hex=SELECTED_COLOR)

def _paint_hidden_hover_brackets(painter, window, plugin) -> None:
    if not REGION_CORNER_BRACKETS:
        return
    region = getattr(plugin, 'region', None)
    edges_fn = getattr(region, 'edges', None)
    if not callable(edges_fn):
        return
    if not STARTUP_REGION_CORNER_BRACKETS:
        mh = getattr(plugin, '_region_mouse', None)
        if mh is None or not getattr(mh, 'hover_hidden', False):
            return
    paint_selection_box(painter, window, edges_fn(), color_hex=LOCKED_COLOR)

def _register_label_painter(window, plugin) -> None:
    if not hasattr(window, '_widget'):
        return
    ovs = getattr(window._widget, '_underlay_painters', None)
    if ovs is None:
        return

    def _paint(painter, w: int, h: int, depth) -> None:
        reg = get_registry(window)
        if (reg.count() <= 1 or not plugin.region_visible
                or plugin not in reg.members):
            return
        paint_region_label(
            painter, window, plugin.region,
            plugin.overlay_label or 'REGION',
            color=reg.color_for(plugin),
            bold=reg.is_selected(plugin),
        )
    ovs.append(_paint)

def _register_keyframes_marker_painter(
    window, plugin, region_palette: RegionPalette | None,
) -> None:
    if not hasattr(window, '_widget'):
        return
    ovs = getattr(window._widget, '_underlay_painters', None)
    if ovs is None:
        return
    color_hex = getattr(region_palette, 'color', None)

    def _paint(painter, w: int, h: int, depth) -> None:
        if not _is_registered(window, plugin):
            return
        if not plugin.keyframes_visible:
            return
        if plugin.keyframes.count() == 0:
            return
        viewmat = getattr(window, '_viewmat', None)
        K = getattr(window, '_K', None)
        if viewmat is None or K is None:
            return
        ortho = getattr(window, '_camera_model', 'pinhole') == 'ortho'
        markers = compute_region_volume_keyframe_markers(
            plugin.keyframes.items(), viewmat, K, ortho=ortho,
        )
        paint_region_volume_keyframes(painter, markers, color_hex=color_hex)
    ovs.append(_paint)

_TOOL_PAINTERS: dict[str, callable] = {
    TOOL_TRANSLATE: paint_translate_region_volume,
    TOOL_SCALE:     paint_scale_region_volume,
    TOOL_ROTATE:    paint_rotate_region_volume,
}

def _make_overlay_painter(window, binding: _ControllerBinding):
    def _paint(painter, w: int, h: int, depth) -> None:
        ctrl = binding.controller
        if not _is_registered(window, ctrl):
            return
        if not ctrl.is_visible():
            return
        _paint_tool_region_volume(painter, window, binding, w)
    return _paint

_AXIS_HOVER_KINDS: frozenset[str] = frozenset(
    {'translate_axis', 'scale_axis', 'rotate_axis'},
)

def _paint_tool_region_volume(
    painter, window, binding: _ControllerBinding, w: int = 0,
) -> None:
    ctrl = binding.controller
    paint_fn = _TOOL_PAINTERS.get(ctrl.tool_mode)
    if paint_fn is None:
        return
    target = ctrl.target
    anchor = target.center.astype(np.float32)
    axes = region_gizmo_axes(target.rotation)
    world_len = region_volume_world_length(
        window, anchor, REGION_VOLUME_SCREEN_LEN_PX,
    )
    hover_axis: int | None = None
    hv = binding.mouse.hover
    if hv is not None:
        kind, idx = hv
        if kind in _AXIS_HOVER_KINDS:
            hover_axis = idx
    if paint_fn is paint_translate_region_volume:
        paint_fn(
            painter, window, anchor, axes, world_len, hover_axis,
            binding.palette, w,
        )
    else:
        paint_fn(
            painter, window, anchor, axes, world_len, hover_axis,
            binding.palette,
        )
    if getattr(binding.mouse, 'shift_active', False):
        paint_region_volume_shift_indicator(
            painter, window, anchor, binding.palette,
        )
