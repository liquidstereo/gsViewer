from process.component.region_volume.attr_common import (
    annotation_duration_spec, compose_specs, keyframe_button_specs,
    shape_spec,
)
from process.component.region_volume.attach import attach_box_plugin
from process.component.region_volume.attr_section import register_box_attr_section
from process.component.region_volume.controller import RegionVolumeBoxController
from process.component.region_volume.factory import (
    is_box_shape, make_region, make_region_painter_override,
)
from process.component.region_volume.key_router import (
    bind_key, bind_num_keys, bind_release_key,
)
from process.component.region_volume.help import box_help_entries
from process.component.region_volume.hover_select import (
    hover_winner, region_is_selected,
)
from process.component.region_volume.keyframe_animation import RegionVolumeKeyframeAnimator
from process.component.region_volume.keyframes import RegionVolumeKeyframes
from process.component.region_volume.keys import (
    make_reset, make_set_tool, make_toggle_visible, show_message_overlay,
)
from process.component.region_volume.label import paint_region_label
from process.component.region_volume.palette_auto import auto_hue_color
from process.component.region_volume.registry import (
    RegionVolumeRegistry, get_registry,
)
from process.component.region_volume.keys_keyframes import (
    make_add_keyframe, make_clear_keyframes,
    make_goto_keyframe, make_remove_keyframe,
)
from process.component.region_volume.manager import (
    register_box_controller, register_controller,
)
from process.component.region_volume.mouse import RegionVolumeController, RegionVolumeMouseHandler
from process.component.region_volume.overlay import (
    RegionPalette, compute_region_segments, locked_palette,
    paint_region, paint_region_faces, paint_region_hull,
    resolve_palette,
)
from process.component.region_volume.overlay_capsule import (
    compute_capsule_segments, make_capsule_painter, paint_capsule_region,
)
from process.component.region_volume.overlay_cone import (
    compute_cone_segments, make_cone_painter, paint_cone_region,
)
from process.component.region_volume.overlay_cylinder import (
    compute_cylinder_segments, make_cylinder_painter,
    paint_cylinder_region,
)
from process.component.region_volume.overlay_sphere import (
    compute_sphere_segments, make_sphere_painter, paint_sphere_region,
)
from process.component.region_volume.overlay_torus import (
    compute_torus_segments, make_torus_painter, paint_torus_region,
)
from process.component.region_volume.paint import RegionVolumePalette
from process.component.region_volume.paint_handles import (
    paint_rotate_region_volume, paint_scale_region_volume,
)
from process.component.region_volume.picking_shapes import (
    ray_capsule, ray_cone, ray_cylinder, ray_ellipsoid,
)
from process.component.region_volume.polygon import (
    PolygonDrawController, RegionPolygon, make_polygon_painter,
    register_polygon_drawing,
)
from process.component.ramp import (
    RampCurve, RegionRampState, apply_ramp_mult, flat_points, ramp_specs,
    ramp_val, region_inside, to_local_norm,
)
from process.component.region_volume.region import RegionBox
from process.component.region_volume.region_capsule import RegionCapsule
from process.component.region_volume.region_cone import RegionCone
from process.component.region_volume.region_cylinder import RegionCylinder
from process.component.region_volume.region_sphere import RegionSphere
from process.component.region_volume.region_torus import RegionTorus
from process.component.region_volume.settings import (
    VOLUME_SHAPE, VOLUME_SHAPE_CAPSULE, VOLUME_SHAPE_CONE,
    VOLUME_SHAPE_CUBE, VOLUME_SHAPE_CYLINDER, VOLUME_SHAPE_POLYGON,
    VOLUME_SHAPE_SPHERE, VOLUME_SHAPE_TORUS, VOLUME_SHAPES,
)
from process.component.region_volume.target import TransformTarget, identity_rotation

__all__ = [
    'RegionVolumeBoxController', 'RegionVolumeController', 'RegionVolumeKeyframeAnimator',
    'RegionVolumeKeyframes', 'RegionVolumeMouseHandler', 'RegionVolumePalette',
    'RegionVolumeRegistry', 'get_registry', 'register_box_attr_section',
    'compose_specs', 'shape_spec', 'annotation_duration_spec',
    'keyframe_button_specs', 'box_help_entries', 'attach_box_plugin',
    'bind_key', 'bind_release_key',
    'bind_num_keys', 'auto_hue_color', 'paint_region_label',
    'RegionBox',
    'RegionCapsule', 'RegionCone', 'RegionCylinder', 'RegionPalette',
    'RegionPolygon', 'RegionSphere', 'RegionTorus',
    'PolygonDrawController', 'make_polygon_painter',
    'register_polygon_drawing',
    'RampCurve', 'RegionRampState', 'apply_ramp_mult', 'flat_points',
    'ramp_specs', 'ramp_val', 'region_inside', 'to_local_norm',
    'TransformTarget', 'compute_capsule_segments', 'compute_cone_segments',
    'compute_cylinder_segments', 'compute_torus_segments',
    'compute_region_segments', 'compute_sphere_segments',
    'identity_rotation', 'is_box_shape',
    'locked_palette', 'resolve_palette', 'paint_region_hull',
    'region_is_selected', 'hover_winner', 'make_add_keyframe',
    'make_clear_keyframes', 'make_capsule_painter', 'make_cone_painter',
    'make_cylinder_painter', 'make_torus_painter',
    'make_goto_keyframe', 'make_region',
    'make_region_painter_override',
    'make_remove_keyframe',
    'make_reset', 'make_set_tool', 'make_sphere_painter',
    'make_toggle_visible',
    'paint_capsule_region', 'paint_cone_region', 'paint_torus_region',
    'paint_cylinder_region', 'paint_region', 'paint_region_faces',
    'paint_rotate_region_volume', 'paint_scale_region_volume', 'paint_sphere_region',
    'ray_capsule', 'ray_cone', 'ray_cylinder', 'ray_ellipsoid',
    'register_box_controller',
    'register_controller', 'show_message_overlay',
    'VOLUME_SHAPE', 'VOLUME_SHAPE_CAPSULE', 'VOLUME_SHAPE_CONE',
    'VOLUME_SHAPE_CUBE', 'VOLUME_SHAPE_CYLINDER', 'VOLUME_SHAPE_POLYGON',
    'VOLUME_SHAPE_SPHERE', 'VOLUME_SHAPE_TORUS', 'VOLUME_SHAPES',
]
