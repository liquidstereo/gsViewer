import logging

from configs.keybinding import (
    SPLAT_SIZE_UP, SPLAT_SIZE_DOWN, SOLO_TOGGLE,
    SLICE_RATIO_UP, SLICE_RATIO_DOWN, SLICE_RATIO_RESET,
)
from configs.settings_effects import (
    SPLAT_SCALE_DEFAULT, SPLAT_SCALE_MIN, SPLAT_SCALE_MAX,
)
from process.keys.slicing import (
    ui_get_ratio, ui_stage_ratio, ui_commit_ratio,
)
from configs.settings_transform import TRANSFORM_KEY_HIDE, TRANSFORM_KEY_LOCK
from process.common import display_name
from process.objects.solo import toggle_object_solo
from process.common.widget import request_repaint
from process.transform.object_keyframe import (
    handle_add_object_keyframe, handle_remove_object_keyframe)
from process.transform.object_reset import reset_selected_object
from process.transform.object_console import (
    apply_object_preset, open_object_console)
from process.transform.object_plugin import apply_plugin_specs
from process.widget.text_case import keep_case
from process.widget.overlays import AttrSection, AttrSpec
from process.widget.overlays.attr_spec import (
    KIND_BOOL, KIND_BUTTON, KIND_FLOAT)

logger = logging.getLogger(__name__)

def _show_spec(window, controller) -> AttrSpec:
    def _get() -> bool:
        sid = controller.selected_id
        return sid is not None and not controller.is_hidden(sid)

    def _set(value: bool) -> None:
        sid = controller.selected_id
        if sid is None:
            return
        if controller.is_hidden(sid) == bool(value):
            controller.toggle_hidden(sid)
            controller.selected_id = sid
        request_repaint(window)

    return AttrSpec(
        'Show', KIND_BOOL, _get, _set,
        tooltip=('Toggle object visibility. '
                 f'Key [{TRANSFORM_KEY_HIDE}].'),
    )

def _lock_spec(window, controller) -> AttrSpec:
    def _get() -> bool:
        sid = controller.selected_id
        return sid is not None and controller.is_locked(sid)

    def _set(value: bool) -> None:
        sid = controller.selected_id
        if sid is None:
            return
        if controller.is_locked(sid) != bool(value):
            controller.toggle_lock(sid)
            controller.selected_id = sid
        request_repaint(window)

    return AttrSpec(
        'Lock', KIND_BOOL, _get, _set,
        tooltip=('Lock object transform (disable tools). '
                 f'Key [{TRANSFORM_KEY_LOCK}].'),
    )

def _solo_spec(window, controller) -> AttrSpec:
    def _get() -> bool:
        sid = controller.selected_id
        return sid is not None and controller.solo_id == sid

    def _set(value: bool) -> None:
        sid = controller.selected_id
        if sid is None:
            return
        if (controller.solo_id == sid) != bool(value):
            toggle_object_solo(window, sid)
        request_repaint(window)

    return AttrSpec(
        'Solo', KIND_BOOL, _get, _set,
        tooltip=('Solo this object (edit only this, hide others). '
                 f'Key [{SOLO_TOGGLE}].'),
    )

def _point_size_spec(window, controller) -> AttrSpec:
    def _get() -> float:
        sid = controller.selected_id
        return controller.get_point_scale(sid) if sid is not None else 1.0

    def _set(value: float) -> None:
        sid = controller.selected_id
        if sid is None:
            return
        mult = max(SPLAT_SCALE_MIN, min(SPLAT_SCALE_MAX, float(value)))
        controller.set_point_scale(sid, mult)
        render = getattr(window, '_render_current', None)
        if render is not None:
            render()
        else:
            request_repaint(window)

    return AttrSpec(
        'Point Size', KIND_FLOAT, _get, _set,
        vmin=0.0, vmax=SPLAT_SCALE_MAX, fmt='{:.3f}x',
        default=SPLAT_SCALE_DEFAULT,
        tooltip=('Adjust this object splat size. Global keys '
                 f'[{SPLAT_SIZE_UP}/{SPLAT_SIZE_DOWN}].'),
    )

def _slice_ratio_spec(window) -> AttrSpec:
    def _get() -> float:
        return ui_get_ratio(window)

    def _set(value: float) -> None:
        ui_stage_ratio(window, value)

    return AttrSpec(
        'Slice Ratio', KIND_FLOAT, _get, _set,
        vmin=0.0, vmax=1.0, fmt='{:.2f}',
        default=1.0,
        on_commit=lambda: ui_commit_ratio(window),
        tooltip=('Runtime stride downsample ratio (VRAM/FPS). Keys '
                 f'[{SLICE_RATIO_DOWN}/{SLICE_RATIO_UP}/'
                 f'{SLICE_RATIO_RESET}].'),
    )

def _object_button_specs(window) -> list:

    return [
        AttrSpec(
            'Set Key', KIND_BUTTON,
            action=lambda: handle_add_object_keyframe(window),
            tooltip='Add a keyframe for the selected object transform.'),
        AttrSpec(
            'Del Key', KIND_BUTTON,
            action=lambda: handle_remove_object_keyframe(window),
            tooltip='Remove the last object transform keyframe.'),
        AttrSpec(
            'Apply', KIND_BUTTON,
            action=lambda: apply_object_preset(window),
            tooltip=('Apply an object preset JSON '
                     '(attributes + random section).')),
        AttrSpec(
            'Reset', KIND_BUTTON,
            action=lambda: reset_selected_object(window),
            tooltip=('Reset selected object transform and point size '
                     'to defaults.')),
        AttrSpec(
            'Script Console', KIND_BUTTON,
            action=lambda: open_object_console(window),
            row_break=True,
            tooltip=('Edit object attributes (Point Size/Position/Scale) '
                     'and the random section. Use expressions like '
                     "POSITION_X: random(10).")),
    ]

def register_object_attr_section(window, controller) -> None:
    sections = getattr(window, '_attr_sections', None)
    if sections is None:
        return
    show = _show_spec(window, controller)
    lock = _lock_spec(window, controller)
    point_size = _point_size_spec(window, controller)
    slice_ratio = _slice_ratio_spec(window)
    solo = _solo_spec(window, controller)
    apply_specs = apply_plugin_specs(window, controller)
    buttons = _object_button_specs(window)

    def _provider():
        if controller.selected_id is None:
            return None
        return [show, lock, solo, point_size, slice_ratio] + apply_specs

    def _title() -> str:
        sid = controller.selected_id
        if sid is None:
            return 'OBJECT'

        if getattr(window, '_chain_segments', None):
            active = getattr(window, '_chain_active_iid', None)
            if active is not None:
                return keep_case(display_name(window, active))
        return keep_case(display_name(window, sid))

    sections.append(AttrSection(_title, _provider))
    _register_object_buttons(window, controller, buttons)
    logger.debug('Object attr section registered')

def _register_object_buttons(window, controller, buttons: list) -> None:

    channel = getattr(window, '_attr_keyframe_buttons', None)
    if channel is None:
        channel = []
        window._attr_keyframe_buttons = channel

    def _provider() -> list:
        if controller.selected_id is None:
            return []
        return buttons

    channel.append(_provider)
