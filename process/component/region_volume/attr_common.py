from configs.keybinding import SOLO_TOGGLE
from configs.settings_annot import (
    ANNOT_ANIM_DURATION, ANNOT_ANIM_DURATION_MAX, ANNOT_ANIM_DURATION_MIN,
)
from process.common.widget import request_repaint
from process.console import open_script_console
from process.undo import record_region_state, snapshot_region_state
from process.widget.overlays import (
    AttrSpec, KIND_BUTTON, KIND_ENUM, KIND_INT,
)
from process.widget.overlays.attr_spec import (
    KIND_BOOL, KIND_CURVE, KIND_FLOAT,
)
from process.component.region_volume.keys import (
    make_apply_override,
)
from process.component.region_volume.keys_keyframes import (
    make_add_keyframe, make_remove_keyframe,
)
from process.component.region_volume.registry import get_registry
from process.component.region_volume.solo import toggle_region_solo
from process.component.region_volume.settings import (
    REGION_SOFTNESS, REGION_SOFTNESS_RANGE, REGION_VOLUME_KEY_KEYFRAME_ADD,
    REGION_VOLUME_KEY_KEYFRAME_REMOVE, REGION_VOLUME_KEY_LOCK,
    REGION_VOLUME_KEY_RESET, REGION_VOLUME_KEY_VISIBLE, VOLUME_SHAPES,
)

def activate_spec(window, plugin) -> AttrSpec | None:
    if not hasattr(plugin, 'is_effect_active'):
        return None

    def _set(value: bool) -> None:
        if bool(value) != bool(plugin.is_effect_active()):
            plugin.toggle_effect_active()
        request_repaint(window)
    key = getattr(plugin, 'effect_key', None)
    tip = 'Toggle effect on/off.'
    if key:
        tip += f' Key [{key}].'
    return AttrSpec(
        'Activate', KIND_BOOL, lambda: bool(plugin.is_effect_active()), _set,
        tooltip=tip,
    )

def lock_spec(window, plugin) -> AttrSpec | None:
    if not hasattr(plugin, 'is_region_locked'):
        return None

    def _set(value: bool) -> None:
        if bool(value) != bool(plugin.is_region_locked()):
            before = snapshot_region_state(plugin)
            plugin.toggle_region_lock()
            after = snapshot_region_state(plugin)
            record_region_state(window, plugin, before, after, 'Region lock')
        request_repaint(window)
    return AttrSpec(
        'Lock', KIND_BOOL, lambda: bool(plugin.is_region_locked()), _set,
        tooltip=('Lock region transform (disable tools). '
                 f'Key [{REGION_VOLUME_KEY_LOCK}].'),
    )

def solo_spec(window, plugin) -> AttrSpec:
    reg = get_registry(window)

    def _set(value: bool) -> None:
        if reg.is_soloed(plugin) != bool(value):
            toggle_region_solo(window, plugin)
        request_repaint(window)
    return AttrSpec(
        'Solo', KIND_BOOL, lambda: reg.is_soloed(plugin), _set,
        tooltip=('Solo this region (edit only this, block others). '
                 f'Key [{SOLO_TOGGLE}].'),
    )

def show_spec(window, plugin) -> AttrSpec:
    def _set(value: bool) -> None:
        plugin.region_visible = bool(value)
        request_repaint(window)
    return AttrSpec(
        'Show', KIND_BOOL, lambda: bool(plugin.region_visible), _set,
        tooltip=('Toggle region box visibility. '
                 f'Key [{REGION_VOLUME_KEY_VISIBLE}].'),
    )

def script_console_spec(window, plugin) -> AttrSpec:
    return AttrSpec(
        'Script Console', KIND_BUTTON,
        action=lambda: open_script_console(window, plugin),
        row_break=True,
        tooltip=('Open settings editor. Save As exports a preset; '
                 'Apply JSON Settings applies a saved preset.'),
    )

def softness_spec(window, plugin) -> AttrSpec:
    region = plugin.region

    def _set(value: float) -> None:
        region.softness = float(value)
        request_repaint(window)
    return AttrSpec(
        'Softness', KIND_FLOAT, lambda: region.softness, _set,
        *REGION_SOFTNESS_RANGE,
        default=getattr(plugin, '_softness_default', REGION_SOFTNESS),
        tooltip='Region boundary softness (falloff width).',
    )

def shape_spec(window, plugin) -> AttrSpec:
    def _set(value: str) -> None:
        plugin.rebuild_region(value)
        request_repaint(window)
    return AttrSpec(
        'Shape', KIND_ENUM, lambda: plugin.shape, _set,
        options=VOLUME_SHAPES,
        default=getattr(plugin, '_default_shape', None),
        tooltip='Region shape: cube/sphere/cylinder/cone/capsule/torus.',
    )

def annotation_duration_spec(window) -> AttrSpec | None:
    anim = getattr(window, '_annot_animator', None)
    if anim is None:
        return None
    return AttrSpec(
        'Anim Dur(ms)', KIND_INT, lambda: anim.duration_ms,
        anim.set_duration_ms, ANNOT_ANIM_DURATION_MIN,
        ANNOT_ANIM_DURATION_MAX, fmt='{:.0f}',
        default=ANNOT_ANIM_DURATION,
        tooltip='Annotation move duration in milliseconds.',
    )

def keyframe_button_specs(window, plugin) -> list:
    add = make_add_keyframe(plugin)
    remove = make_remove_keyframe(plugin)
    apply_fn = make_apply_override(plugin)
    reset = plugin.reset_to_default
    return [
        AttrSpec('Set Key', KIND_BUTTON, action=lambda: add(window),
                 tooltip=('Add a region keyframe. '
                          f'Key [{REGION_VOLUME_KEY_KEYFRAME_ADD}].')),
        AttrSpec('Del Key', KIND_BUTTON, action=lambda: remove(window),
                 tooltip=('Remove the last region keyframe. '
                          f'Key [{REGION_VOLUME_KEY_KEYFRAME_REMOVE}].')),
        AttrSpec('Apply', KIND_BUTTON, action=lambda: apply_fn(window),
                 tooltip=('Apply a preset JSON '
                          '(constants/attrs/transform/curves).')),
        AttrSpec('Reset', KIND_BUTTON, action=lambda: reset(window),
                 tooltip=('Reset region transform and parameters to '
                          f'defaults. Key [{REGION_VOLUME_KEY_RESET}].')),
    ]

def compose_specs(window, plugin, specific: list) -> list:
    specs = []
    activate = activate_spec(window, plugin)
    if activate is not None:
        specs.append(activate)
    specs.append(show_spec(window, plugin))
    lock = lock_spec(window, plugin)
    if lock is not None:
        specs.append(lock)
    specs.append(solo_spec(window, plugin))
    for provider in getattr(window, '_box_extra_spec_providers', ()) or ():
        extra = provider(window, plugin)
        if extra:
            specs.extend(extra)
    specs.append(shape_spec(window, plugin))
    specs.extend(specific)
    specs.append(softness_spec(window, plugin))
    curves = [s for s in specs if s.kind == KIND_CURVE]
    if curves:
        specs = [s for s in specs if s.kind != KIND_CURVE] + curves
    return specs
