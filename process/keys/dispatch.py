import logging
import configs.keybinding as _kb
from collections.abc import Callable
from PySide6.QtCore import Qt
from configs.keybinding import (
    KEY_PLAY_PAUSE, KEY_PREV_FRAME,
    KEY_NEXT_FRAME, KEY_FIRST_FRAME, KEY_LAST_FRAME, KEY_QUIT,
    TOGGLE_OVERLAY,
    TOGGLE_PLUGIN_HELP,
    TOGGLE_WORLD_ROT,
    TOGGLE_MESH, TOGGLE_COLORMAP,
    TOGGLE_DEPTH_OCCLUSION, TOGGLE_CORNER_BRACKET, THEME_CYCLE,
    TOGGLE_LOGS, TOGGLE_FOG,
    TOGGLE_SEQUENCE_OVERLAY, TOGGLE_ALL_OVERLAYS, TOGGLE_ATTR_OVERLAY,
    TOGGLE_PREVIEW_OVERLAYS,
    RESET_CAM, TURNTABLE_TOGGLE, RESET_ALL, RECORD_TOGGLE, OBJECT_RESET,
    CAM_KEY_ADD, CAM_KEY_REMOVE, CAM_KEY_TOGGLE,
    CAM_KEY_GOTO_NEXT, CAM_KEY_GOTO_PREV,
    CAM_KEY_CLEAR,
    OBJ_KEY_ADD, OBJ_KEY_REMOVE, OBJ_KEY_CLEAR,
    OBJ_KEY_GOTO_NEXT, OBJ_KEY_GOTO_PREV, OBJ_KEY_TOGGLE,
    GLOBAL_KEY_ADD, GLOBAL_KEY_REMOVE, GLOBAL_KEY_CLEAR,
    GLOBAL_KEY_GOTO_NEXT, GLOBAL_KEY_GOTO_PREV, GLOBAL_KEY_TOGGLE,
    DELETE_SELECTED,
    SCREENSHOT, SOLO_TOGGLE,
    ORTHO_CAM_FRONT, ORTHO_CAM_BACK, ORTHO_CAM_LEFT,
    ORTHO_CAM_RIGHT, ORTHO_CAM_TOP, ORTHO_CAM_BOTTOM,
    MODE_DEFAULT, MODE_NORMAL, MODE_POINT,
    MODE_ANISO, MODE_OPACITY,
    MODE_HIT_COUNT, MODE_ACCUMULATION, MODE_SCALE,
    MODE_GL_POINTS, MODE_ROTATION, MODE_MEDIAN_DEPTH,
    SPLAT_SIZE_UP, SPLAT_SIZE_DOWN, SPLAT_SIZE_RESET,
    SLICE_RATIO_UP, SLICE_RATIO_DOWN, SLICE_RATIO_RESET,
    OBJECT_ISOLATE_KEYS,
)
from process.objects.keys import make_isolate_handler
from process.objects.solo import handle_solo
from process.keys import playback, effects
from process.keys import camera as cam_keys
from process.reset.keys import handle_reset_all
from process.transform.keys import handle_object_reset
from process.annotation import keys as annot_keys
from process.transform import object_keyframe as obj_kf
from process.transform import global_keyframe as glob_kf
from process.effects import colormap
from process.keys import screenshot as screenshot_keys
from process.keys import slicing as slice_keys
from process.mode import keys as mode_keys
from process.undo import keys as undo_keys
from process.keys.delete import handle_delete
from process.data.pointcloud_caps import notify_if_unsupported

logger = logging.getLogger(__name__)

def _build_qt_key_map() -> dict[Qt.Key, str]:
    result = {}
    for val in vars(_kb).values():
        if not isinstance(val, str):
            continue
        try:
            result[getattr(Qt.Key, f'Key_{val}')] = val
        except AttributeError:
            pass
    return result

_QT_KEY_MAP: dict[Qt.Key, str] = _build_qt_key_map()

_KP = Qt.KeyboardModifier.KeypadModifier
_SH = Qt.KeyboardModifier.ShiftModifier
_CT = Qt.KeyboardModifier.ControlModifier
_AL = Qt.KeyboardModifier.AltModifier

_QT_KEY_MOD_MAP: dict[
    Qt.Key, list[tuple[Qt.KeyboardModifier, str]]
] = {
    Qt.Key.Key_0:      [(_AL | _KP, 'Alt+Num0')],

    Qt.Key.Key_1:      [(_AL, 'Alt+1'), (_SH, 'Shift+1')],
    Qt.Key.Key_2:      [(_AL, 'Alt+2'), (_SH, 'Shift+2')],
    Qt.Key.Key_3:      [(_AL, 'Alt+3'), (_SH, 'Shift+3')],
    Qt.Key.Key_4:      [(_AL, 'Alt+4'), (_SH, 'Shift+4')],
    Qt.Key.Key_5:      [(_AL, 'Alt+5'), (_SH, 'Shift+5')],
    Qt.Key.Key_6:      [(_AL, 'Alt+6'), (_SH, 'Shift+6')],
    Qt.Key.Key_7:      [(_AL, 'Alt+7'), (_SH, 'Shift+7')],
    Qt.Key.Key_8:      [(_AL, 'Alt+8'), (_SH, 'Shift+8')],
    Qt.Key.Key_9:      [(_AL, 'Alt+9'), (_SH, 'Shift+9')],

    Qt.Key.Key_Exclam:      [(_AL | _SH, 'Alt+Shift+1'), (_SH, 'Shift+1')],
    Qt.Key.Key_At:          [(_AL | _SH, 'Alt+Shift+2'), (_SH, 'Shift+2')],
    Qt.Key.Key_NumberSign:  [(_AL | _SH, 'Alt+Shift+3'), (_SH, 'Shift+3')],
    Qt.Key.Key_Dollar:      [(_AL | _SH, 'Alt+Shift+4'), (_SH, 'Shift+4')],
    Qt.Key.Key_Percent:     [(_AL | _SH, 'Alt+Shift+5'), (_SH, 'Shift+5')],
    Qt.Key.Key_AsciiCircum: [(_AL | _SH, 'Alt+Shift+6'), (_SH, 'Shift+6')],
    Qt.Key.Key_Ampersand:   [(_AL | _SH, 'Alt+Shift+7'), (_SH, 'Shift+7')],
    Qt.Key.Key_Asterisk:    [(_AL | _SH, 'Alt+Shift+8'), (_SH, 'Shift+8')],
    Qt.Key.Key_ParenLeft:   [(_AL | _SH, 'Alt+Shift+9'), (_SH, 'Shift+9')],
    Qt.Key.Key_Period: [
        (_AL | _KP, 'Alt+NumDecimal'),
        (_KP,       'NumDecimal'),
    ],

    Qt.Key.Key_Delete: [
        (_AL | _SH, 'Alt+Shift+Delete'),
        (_CT,       'Ctrl+Delete'),
        (_AL,       'Alt+Delete'),
        (_SH,       'Shift+Delete'),
        (Qt.KeyboardModifier.NoModifier, DELETE_SELECTED),
    ],

    Qt.Key.Key_A: [
        (_AL | _SH, 'Alt+Shift+A'),
        (_CT, 'Ctrl+A'), (_SH, 'Shift+A'), (_AL, 'Alt+A'),
    ],

    Qt.Key.Key_Z: [(_CT, 'Ctrl+Z')],
    Qt.Key.Key_Y: [(_CT, 'Ctrl+Y')],

    Qt.Key.Key_B:        [(_CT, THEME_CYCLE), (_SH, 'Shift+B')],
    Qt.Key.Key_V:        [(_SH, 'Shift+V')],

    Qt.Key.Key_P: [
        (_AL | _SH, 'Alt+Shift+P'), (_SH, 'Shift+P'), (_AL, 'Alt+P'),
    ],
    Qt.Key.Key_J:        [(_SH, 'Shift+J')],
    Qt.Key.Key_W:        [(_CT, 'Ctrl+W'), (_SH, 'Shift+W')],
    Qt.Key.Key_E:        [(_CT, 'Ctrl+E'), (_SH, 'Shift+E')],

    Qt.Key.Key_R: [
        (_CT | _SH, 'Ctrl+Shift+R'), (_AL | _SH, 'Alt+Shift+R'),
        (_CT, 'Ctrl+R'), (_SH, 'Shift+R'), (_AL, 'Alt+R'),
    ],

    Qt.Key.Key_Home: [(_CT, 'Ctrl+Home')],

    Qt.Key.Key_D: [
        (_CT | _SH, 'Ctrl+Shift+D'), (_AL | _SH, 'Alt+Shift+D'),
        (_SH, 'Shift+D'), (_AL, 'Alt+D'),
    ],
    Qt.Key.Key_F5:       [(_AL, 'Alt+F5')],
    Qt.Key.Key_F6:       [(_AL, 'Alt+F6')],
    Qt.Key.Key_F7:       [(_AL, 'Alt+F7')],
    Qt.Key.Key_F8:       [(_AL, 'Alt+F8')],
    Qt.Key.Key_F9:       [(_AL, 'Alt+F9')],
    Qt.Key.Key_F10:      [(_AL, 'Alt+F10')],

    Qt.Key.Key_PageUp: [
        (_CT, 'Ctrl+PageUp'),
        (_AL | _SH, 'Alt+Shift+PageUp'),
        (_AL, 'Alt+PageUp'), (_SH, 'Shift+PageUp'),
    ],
    Qt.Key.Key_PageDown: [
        (_CT, 'Ctrl+PageDown'),
        (_AL | _SH, 'Alt+Shift+PageDown'),
        (_AL, 'Alt+PageDown'), (_SH, 'Shift+PageDown'),
    ],

    Qt.Key.Key_Plus:     [(_SH | _KP, 'Shift+Num+')],
    Qt.Key.Key_Minus:    [(_SH | _KP, 'Shift+Num-')],

    Qt.Key.Key_BracketLeft:  [
        (_CT, 'Ctrl+['), (Qt.KeyboardModifier.NoModifier, '['),
    ],
    Qt.Key.Key_BracketRight: [
        (_CT, 'Ctrl+]'), (Qt.KeyboardModifier.NoModifier, ']'),
    ],

    Qt.Key.Key_Backslash: [(_CT, 'Ctrl+Backslash')],
}

def _region_lifecycle(attr: str) -> Callable:
    def _handler(win) -> None:
        cb = getattr(win, attr, None)
        if callable(cb):
            cb()
    return _handler

def handle_theme_cycle(win) -> None:
    from process.theme import cycle_theme
    cycle_theme(win)

_HANDLERS: dict[str, Callable] = {
    TOGGLE_OVERLAY:          effects.handle_toggle_help,
    TOGGLE_PLUGIN_HELP:      effects.handle_toggle_plugin_help,
    TOGGLE_WORLD_ROT:       effects.handle_cycle_world_rot,
    KEY_PLAY_PAUSE:         playback.handle_play_pause,
    KEY_PREV_FRAME:         playback.handle_prev_frame,
    KEY_NEXT_FRAME:         playback.handle_next_frame,
    KEY_FIRST_FRAME:        playback.handle_first_frame,
    KEY_LAST_FRAME:         playback.handle_last_frame,
    KEY_QUIT:               playback.handle_quit,
    TOGGLE_MESH:            effects.handle_toggle_mesh,
    TOGGLE_COLORMAP:        colormap.handle_toggle_colormap,
    TOGGLE_DEPTH_OCCLUSION: effects.handle_toggle_depth_occlusion,
    TOGGLE_CORNER_BRACKET:  effects.handle_toggle_corner_bracket,
    TOGGLE_LOGS:            effects.handle_toggle_logs,
    TOGGLE_FOG:             effects.handle_toggle_fog,
    TOGGLE_SEQUENCE_OVERLAY: effects.handle_toggle_sequence_overlay,
    TOGGLE_ALL_OVERLAYS:    effects.handle_toggle_all_overlays,
    TOGGLE_ATTR_OVERLAY:    effects.handle_toggle_attr_overlay,
    TOGGLE_PREVIEW_OVERLAYS: effects.handle_toggle_preview_overlays,
    TURNTABLE_TOGGLE:          effects.handle_toggle_turntable,
    RESET_CAM:              cam_keys.handle_reset_camera,
    RESET_ALL:              handle_reset_all,
    RECORD_TOGGLE:          effects.handle_record_toggle,
    OBJECT_RESET:           handle_object_reset,
    ORTHO_CAM_FRONT:        cam_keys.handle_ortho_front,
    ORTHO_CAM_BACK:         cam_keys.handle_ortho_back,
    ORTHO_CAM_LEFT:         cam_keys.handle_ortho_left,
    ORTHO_CAM_RIGHT:        cam_keys.handle_ortho_right,
    ORTHO_CAM_TOP:          cam_keys.handle_ortho_top,
    ORTHO_CAM_BOTTOM:       cam_keys.handle_ortho_bottom,
    CAM_KEY_ADD:          annot_keys.handle_add_annotation,
    CAM_KEY_REMOVE:       annot_keys.handle_remove_annotation,
    CAM_KEY_TOGGLE:       annot_keys.handle_toggle_annotations,
    CAM_KEY_CLEAR:        annot_keys.handle_clear_all,
    CAM_KEY_GOTO_NEXT:    annot_keys.handle_goto_next_annotation,
    CAM_KEY_GOTO_PREV:    annot_keys.handle_goto_prev_annotation,
    OBJ_KEY_ADD:             obj_kf.handle_add_object_keyframe,
    OBJ_KEY_REMOVE:          obj_kf.handle_remove_object_keyframe,
    OBJ_KEY_CLEAR:           obj_kf.handle_clear_object_keyframes,
    OBJ_KEY_GOTO_NEXT:       obj_kf.handle_goto_next_object_keyframe,
    OBJ_KEY_GOTO_PREV:       obj_kf.handle_goto_prev_object_keyframe,
    OBJ_KEY_TOGGLE:          obj_kf.handle_toggle_object_keyframes,
    GLOBAL_KEY_ADD:          glob_kf.handle_add_global_keyframe,
    GLOBAL_KEY_REMOVE:       glob_kf.handle_remove_global_keyframe,
    GLOBAL_KEY_CLEAR:        glob_kf.handle_clear_global_keyframes,
    GLOBAL_KEY_GOTO_NEXT:    glob_kf.handle_goto_next_global_keyframe,
    GLOBAL_KEY_GOTO_PREV:    glob_kf.handle_goto_prev_global_keyframe,
    GLOBAL_KEY_TOGGLE:       glob_kf.handle_toggle_global_keyframes,
    SCREENSHOT:             screenshot_keys.handle_screenshot,
    SOLO_TOGGLE:            handle_solo,
    MODE_DEFAULT:           mode_keys.handle_mode_default,
    MODE_NORMAL:            mode_keys.handle_mode_normal,
    MODE_POINT:             mode_keys.handle_mode_point,
    MODE_ANISO:             mode_keys.handle_mode_aniso,
    MODE_OPACITY:           mode_keys.handle_mode_opacity,
    MODE_HIT_COUNT:         mode_keys.handle_mode_hit_count,
    MODE_ACCUMULATION:      mode_keys.handle_mode_accumulation,
    MODE_SCALE:             mode_keys.handle_mode_scale,
    MODE_GL_POINTS:         mode_keys.handle_mode_gl_points,
    MODE_ROTATION:          mode_keys.handle_mode_rotation,
    MODE_MEDIAN_DEPTH:      mode_keys.handle_mode_median_depth,
    SPLAT_SIZE_UP:          mode_keys.handle_splat_size_up,
    SPLAT_SIZE_DOWN:        mode_keys.handle_splat_size_down,
    SPLAT_SIZE_RESET:       mode_keys.handle_splat_size_reset,
    SLICE_RATIO_UP:         slice_keys.handle_slice_ratio_up,
    SLICE_RATIO_DOWN:       slice_keys.handle_slice_ratio_down,
    SLICE_RATIO_RESET:      slice_keys.handle_slice_ratio_reset,
    THEME_CYCLE:            handle_theme_cycle,
    DELETE_SELECTED:        handle_delete,
    'Ctrl+Z':               undo_keys.handle_undo,
    'Ctrl+Y':               undo_keys.handle_redo,
    'Ctrl+Shift+R':         _region_lifecycle('_region_delete_cb'),
    'Ctrl+Shift+D':         _region_lifecycle('_region_duplicate_cb'),
}

for _i, _key in enumerate(OBJECT_ISOLATE_KEYS):
    _HANDLERS[_key] = make_isolate_handler(_i)

def _consume_solo_activate(win, key_name: str) -> bool:
    if key_name != getattr(win, '_attr_solo_key', None):
        return False
    toggle = getattr(win, '_attr_solo_toggle', None)
    if not callable(toggle):
        return False

    from process.transform.attr_overlay import (
        attr_solo_active, has_active_selection,
    )

    if has_active_selection(win):
        return False
    if attr_solo_active(win, getattr(win, '_attr_solo_flag', None)):
        return False
    toggle()
    return True

def _resolve_plugin_key(win, qt_key: Qt.Key) -> str | None:
    for key_char in getattr(win, '_extra_handlers', {}).keys():
        try:
            if getattr(Qt.Key, f'Key_{key_char}') == qt_key:
                return key_char
        except AttributeError:
            continue
    return None

def dispatch(
    win,
    qt_key: Qt.Key,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    auto_repeat: bool = False,
) -> bool:
    mod_entries = _QT_KEY_MOD_MAP.get(qt_key)
    key_name: str | None = None
    if mod_entries is not None:
        for required, mod_name in mod_entries:
            if (modifiers & required) == required:
                key_name = mod_name
                break
    if key_name is None:
        key_name = _QT_KEY_MAP.get(qt_key)
    if key_name is None:
        key_name = _resolve_plugin_key(win, qt_key)
    if key_name is None:
        return False
    if auto_repeat and key_name not in getattr(win, '_repeatable_keys', ()):
        return False
    if _consume_solo_activate(win, key_name):
        return True
    handler = _HANDLERS.get(key_name)
    if handler is None:
        handler = getattr(win, '_extra_handlers', {}).get(key_name)
    if handler is None:
        logger.debug('No handler for key: %s', key_name)
        return False
    notify_if_unsupported(win, handler)
    handler(win)
    return True
