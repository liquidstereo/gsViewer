import logging
from collections.abc import Callable

from configs.settings_transform import (
    TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
    TRANSFORM_KEY_HIDE, TRANSFORM_KEY_LOCK, TRANSFORM_KEY_TOOL_ROTATE,
    TRANSFORM_KEY_TOOL_SCALE, TRANSFORM_KEY_TOOL_TRANSLATE,
)
from process.common import display_name
from process.common.widget import set_message_overlay
from process.handle import overlay_event
from process.transform.controller import InputTransformController
from process.undo import record_object_state, snapshot_object_state

logger = logging.getLogger(__name__)

_TOOL_LABEL: dict[str, str] = {
    TOOL_TRANSLATE: 'TRANSLATE',
    TOOL_ROTATE:    'ROTATE',
    TOOL_SCALE:     'SCALE',
}

def _make_set_tool(
    controller: InputTransformController, tool: str, fallback: Callable | None,
) -> Callable:
    def handler(win) -> None:
        if controller.selected_id is None:
            if fallback is not None:
                fallback(win)
            return
        if controller.tool_mode == tool:
            return
        controller.tool_mode = tool
        label = _TOOL_LABEL.get(tool)
        if label is not None:
            set_message_overlay(win, f'{controller.selected_id} {label}')
        tgt = f'Object({display_name(win, controller.selected_id)})'
        overlay_event(logger, tgt, 'Update', attr='Tool', value=tool,
                      to_file=True)
        controller.on_change()
    return handler

def _make_toggle_lock(
    controller: InputTransformController, fallback: Callable | None,
) -> Callable:
    def handler(win) -> None:
        sel = controller.selected_id
        if sel is None:
            before = snapshot_object_state(win, controller)
            unlocked = controller.unlock_last()
            if unlocked is not None:
                controller.select(unlocked)
                controller.on_change()
                record_object_state(
                    win, controller, before,
                    snapshot_object_state(win, controller), 'Unlock',
                )
                return
            if fallback is not None:
                fallback(win)
            return
        before = snapshot_object_state(win, controller)
        controller.toggle_lock(sel)
        controller.on_change()
        record_object_state(
            win, controller, before,
            snapshot_object_state(win, controller), 'Lock',
        )
    return handler

def _make_toggle_hide(
    controller: InputTransformController, fallback: Callable | None,
) -> Callable:
    def handler(win) -> None:
        sel = controller.selected_id
        if sel is None:
            before = snapshot_object_state(win, controller)
            shown = controller.unhide_last()
            if shown is not None:
                controller.select(shown)
                set_message_overlay(win, f'{shown} SHOWN')
                controller.on_change()
                record_object_state(
                    win, controller, before,
                    snapshot_object_state(win, controller), 'Hide',
                )
                return
            if fallback is not None:
                fallback(win)
            return
        before = snapshot_object_state(win, controller)
        hidden = controller.toggle_hidden(sel)
        state = 'HIDDEN' if hidden else 'SHOWN'
        set_message_overlay(win, f'{sel} {state}')
        controller.on_change()
        record_object_state(
            win, controller, before,
            snapshot_object_state(win, controller), 'Hide',
        )
    return handler

def handle_object_reset(win) -> None:
    ctrl = getattr(win, '_input_transform', None)
    if ctrl is None:
        return
    sid = ctrl.selected_id
    if sid is None:
        return
    target = ctrl.targets.get(sid)
    if target is not None:
        target.reset()
    set_message_overlay(win, f'{sid} RESET')
    tgt = f'Object({display_name(win, sid)})'
    overlay_event(logger, tgt, 'Reset', to_file=True)
    ctrl.on_change()

def register_keys(
    window, controller: InputTransformController,
) -> None:
    eh = getattr(window, '_extra_handlers', None)
    if eh is None:
        return
    for key, tool in (
        (TRANSFORM_KEY_TOOL_TRANSLATE, TOOL_TRANSLATE),
        (TRANSFORM_KEY_TOOL_ROTATE,    TOOL_ROTATE),
        (TRANSFORM_KEY_TOOL_SCALE,     TOOL_SCALE),
    ):
        prev = eh.get(key)
        eh[key] = _make_set_tool(controller, tool, prev)
    prev_lock = eh.get(TRANSFORM_KEY_LOCK)
    eh[TRANSFORM_KEY_LOCK] = _make_toggle_lock(controller, prev_lock)
    prev_hide = eh.get(TRANSFORM_KEY_HIDE)
    eh[TRANSFORM_KEY_HIDE] = _make_toggle_hide(controller, prev_hide)
