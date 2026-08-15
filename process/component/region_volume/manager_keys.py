import logging

from process.component.region_volume.key_router import bind_key, bind_num_keys
from process.component.region_volume.keys import (
    make_adjust_strength, make_cycle_shape, make_open_console,
    make_reset_to_default, make_set_tool, make_show_attr, make_toggle_lock,
    make_toggle_visible,
)
from process.component.region_volume.keys_keyframes import (
    make_add_keyframe, make_clear_keyframes, make_goto_keyframe,
    make_remove_keyframe, make_toggle_keyframes,
)
from process.component.region_volume.settings import (
    REGION_VOLUME_KEY_KEYFRAME_ADD, REGION_VOLUME_KEY_KEYFRAME_CLEAR,
    REGION_VOLUME_KEY_KEYFRAME_NEXT, REGION_VOLUME_KEY_KEYFRAME_PREV,
    REGION_VOLUME_KEY_KEYFRAME_REMOVE, REGION_VOLUME_KEY_KEYFRAME_TOGGLE,
    REGION_VOLUME_KEY_ATTR, REGION_VOLUME_KEY_CONSOLE,
    REGION_VOLUME_KEY_CYCLE_SHAPE, REGION_VOLUME_KEY_LOCK,
    REGION_VOLUME_KEY_RESET,
    REGION_VOLUME_KEY_STRENGTH_DOWN, REGION_VOLUME_KEY_STRENGTH_UP,
    REGION_VOLUME_KEY_TOOL_ROTATE, REGION_VOLUME_KEY_TOOL_SCALE,
    REGION_VOLUME_KEY_TOOL_TRANSLATE, REGION_VOLUME_KEY_VISIBLE,
    REGION_VOLUME_STRENGTH_STEP, TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
)

logger = logging.getLogger(__name__)

def _register_strength_keys(window, plugin) -> None:
    system = getattr(plugin, 'system', None)
    if system is None or not hasattr(system, 'strength_scale'):
        return
    bind_key(
        window, plugin, REGION_VOLUME_KEY_STRENGTH_UP,
        make_adjust_strength(plugin, REGION_VOLUME_STRENGTH_STEP),
        allow_when_hidden=True,
    )
    bind_key(
        window, plugin, REGION_VOLUME_KEY_STRENGTH_DOWN,
        make_adjust_strength(plugin, -REGION_VOLUME_STRENGTH_STEP),
        allow_when_hidden=True,
    )
    repeatable = getattr(window, '_repeatable_keys', None)
    if repeatable is not None:
        repeatable.add(REGION_VOLUME_KEY_STRENGTH_UP)
        repeatable.add(REGION_VOLUME_KEY_STRENGTH_DOWN)

def register_keys(window, plugin, with_keyframes: bool) -> None:
    if getattr(window, '_extra_handlers', None) is None:
        return
    bind_key(window, plugin, REGION_VOLUME_KEY_VISIBLE,
             make_toggle_visible(plugin))
    bind_key(window, plugin, REGION_VOLUME_KEY_LOCK,
             make_toggle_lock(plugin), allow_when_hidden=True)
    bind_key(window, plugin, REGION_VOLUME_KEY_RESET,
             make_reset_to_default(plugin), allow_when_hidden=True)
    bind_key(window, plugin, REGION_VOLUME_KEY_TOOL_TRANSLATE,
             make_set_tool(plugin, TOOL_TRANSLATE))
    bind_key(window, plugin, REGION_VOLUME_KEY_TOOL_ROTATE,
             make_set_tool(plugin, TOOL_ROTATE))
    bind_key(window, plugin, REGION_VOLUME_KEY_TOOL_SCALE,
             make_set_tool(plugin, TOOL_SCALE))
    bind_key(window, plugin, REGION_VOLUME_KEY_CYCLE_SHAPE,
             make_cycle_shape(plugin), allow_when_hidden=True)
    bind_key(window, plugin, REGION_VOLUME_KEY_CONSOLE,
             make_open_console(plugin), allow_when_hidden=True)
    bind_key(window, plugin, REGION_VOLUME_KEY_ATTR,
             make_show_attr(plugin), allow_when_hidden=True)
    _register_strength_keys(window, plugin)
    bind_num_keys(window)
    if not with_keyframes:
        return
    bind_key(window, plugin, REGION_VOLUME_KEY_KEYFRAME_ADD,
             make_add_keyframe(plugin))
    bind_key(window, plugin, REGION_VOLUME_KEY_KEYFRAME_PREV,
             make_goto_keyframe(plugin, -1))
    bind_key(window, plugin, REGION_VOLUME_KEY_KEYFRAME_NEXT,
             make_goto_keyframe(plugin, +1))
    bind_key(window, plugin, REGION_VOLUME_KEY_KEYFRAME_REMOVE,
             make_remove_keyframe(plugin))
    bind_key(window, plugin, REGION_VOLUME_KEY_KEYFRAME_CLEAR,
             make_clear_keyframes(plugin))
    bind_key(window, plugin, REGION_VOLUME_KEY_KEYFRAME_TOGGLE,
             make_toggle_keyframes(plugin))
