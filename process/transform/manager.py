import logging

import numpy as np

from configs.settings_style import (
    OBJECT_CORNER_BRACKETS, SELECTED_COLOR, SELECTED_LINE_WIDTH,
    LOCKED_COLOR, LOCKED_LINE_WIDTH, LOCKED_ALPHA, LOCK_BRACKET,
)
from configs.settings_transform import TOOL_NONE, TRANSFORM_SCREEN_LEN_PX
from process.common.core import json_output_path
from process.transform.apply import make_frame_processor
from process.transform.attr_persist import load_object_attrs, save_object_attrs
from process.transform.attr_section import register_object_attr_section
from process.transform.controller import InputTransformController
from process.transform.keys import register_keys
from process.transform.mouse import InputTransformMouseHandler
from process.transform.object_keyframe import ObjectKeyframeStore
from process.transform.global_keyframe import GlobalKeyframeStore
from process.overlay_coord import object_gizmo_axes
from process.transform.paint import (
    paint_handles, paint_selection_box, paint_shift_indicator,
)
from process.transform.picking import world_length_for_screen_px

logger = logging.getLogger(__name__)

def _make_bbox_painter(controller: InputTransformController):
    def _paint(painter, w: int, h: int, depth) -> None:
        win = controller._window

        for input_id, target in controller.targets.items():
            if not controller.is_bracket_mode(input_id):
                continue
            paint_selection_box(
                painter, win, target.edges(),
                color_hex=SELECTED_COLOR,
                line_width=SELECTED_LINE_WIDTH,
                alpha=1.0,
            )

        for input_id, target in controller.targets.items():
            if not LOCK_BRACKET:
                break
            if not controller.is_locked(input_id):
                continue
            if controller.is_hidden(input_id):
                continue
            paint_selection_box(
                painter, win, target.edges(),
                color_hex=LOCKED_COLOR,
                line_width=LOCKED_LINE_WIDTH,
                alpha=LOCKED_ALPHA,
            )

        if not OBJECT_CORNER_BRACKETS:
            return
        sel_id = controller.selected_id
        if sel_id is None:
            return
        target = controller.targets.get(sel_id)
        if target is None:
            return
        paint_selection_box(
            painter, win, target.edges(),
            color_hex=SELECTED_COLOR,
            line_width=SELECTED_LINE_WIDTH,
            alpha=1.0,
        )
    return _paint

def _make_handles_painter(
    controller: InputTransformController,
    mouse_handler: InputTransformMouseHandler,
):
    def _paint(painter, w: int, h: int, depth) -> None:
        target = controller.target
        if target is None:
            return

        if controller.tool_mode == TOOL_NONE:
            return
        axes = object_gizmo_axes(target.rotation)
        win = controller._window
        world_len = world_length_for_screen_px(
            win, target.center, TRANSFORM_SCREEN_LEN_PX,
        )
        hover_axis: int | None = None
        hover_uniform = False
        if mouse_handler.hover is not None:
            kind, axis = mouse_handler.hover
            if kind in ('translate_axis', 'scale_axis', 'rotate_axis'):
                hover_axis = axis
            elif kind == 'uniform_center':
                hover_uniform = True
        paint_handles(
            painter, win, controller.tool_mode,
            target.center.astype(np.float32), axes, world_len,
            hover_axis, hover_uniform, w,
        )
        if getattr(mouse_handler, 'shift_active', False):
            paint_shift_indicator(
                painter, win, target.center.astype(np.float32),
            )
    return _paint

def _register_painters(
    window, controller: InputTransformController,
    mouse_handler: InputTransformMouseHandler,
) -> None:
    widget = getattr(window, '_widget', None)
    if widget is None:
        return
    underlay = getattr(widget, '_underlay_painters', None)
    overlay = getattr(widget, '_overlay_painters', None)
    if underlay is not None:
        underlay.append(_make_bbox_painter(controller))
    if overlay is not None:
        overlay.append(_make_handles_painter(controller, mouse_handler))

def _register_object_persistence(window, controller) -> None:
    name = getattr(window, '_json_key', '') or 'default'
    controller.attrs_path = json_output_path(name, '_objects', 'attrs.json')
    controller._saved_attrs = load_object_attrs(controller)
    listeners = getattr(window, '_attr_commit_listeners', None)
    if listeners is None:
        listeners = []
        window._attr_commit_listeners = listeners

    def _on_commit(row) -> None:
        if controller.selected_id is not None:
            save_object_attrs(controller)

    listeners.append(_on_commit)

def register_transform(window) -> InputTransformController:
    controller = InputTransformController(window)
    window._input_transform = controller
    _register_object_persistence(window, controller)
    window._object_keyframes = ObjectKeyframeStore(window)
    window._global_keyframes = GlobalKeyframeStore(window)
    fps = getattr(window, '_frame_processors', None)
    if fps is not None:
        fps.append(make_frame_processor(controller))
    mouse_handler = InputTransformMouseHandler(window, controller)
    mouse_handler.attach()
    register_keys(window, controller)
    _register_painters(window, controller, mouse_handler)
    register_object_attr_section(window, controller)
    logger.info('Input transform attached: W/E/R = translate/rotate/scale')
    return controller
