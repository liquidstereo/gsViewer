from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QFileDialog

from process.common.widget import request_repaint
from process.console.launcher import open_script_console
from process.widget.overlays.attr_spec import (
    CONSOLE_BUTTON_LABEL, STANDARD_BUTTON_LABELS, AttrSpec, KIND_BUTTON,
)

_TIP_SET_KEY = 'Add a parameter keyframe.'
_TIP_DEL_KEY = 'Remove the last keyframe.'
_TIP_APPLY = 'Load parameters from a preset JSON file.'
_TIP_RESET = 'Reset all parameters to settings defaults.'
_TIP_CONSOLE = 'Open the parameter JSON in the script console.'

def preset_dir(plugin) -> str:
    settings_path = plugin.settings_module_path()
    if settings_path is None:
        return ''
    base = Path(settings_path).parent
    preset = base / 'preset'
    try:
        preset.mkdir(parents=True, exist_ok=True)
    except OSError:
        return str(base)
    return str(preset)

def keyframe_buttons(window, plugin, add: Callable, remove: Callable,
                     add_tip: str = _TIP_SET_KEY,
                     del_tip: str = _TIP_DEL_KEY) -> list:
    return [
        AttrSpec(STANDARD_BUTTON_LABELS[0], KIND_BUTTON,
                 action=lambda: add(window),
                 tooltip=add_tip),
        AttrSpec(STANDARD_BUTTON_LABELS[1], KIND_BUTTON,
                 action=lambda: remove(window),
                 tooltip=del_tip),
    ]

def apply_button(window, plugin, after: Callable | None = None) -> AttrSpec:
    def _action() -> None:
        path, _ = QFileDialog.getOpenFileName(
            window, 'Apply JSON Settings', preset_dir(plugin),
            'JSON (*.json)')
        if not path:
            return
        plugin.load_override_from(path)
        if after is not None:
            after()
        request_repaint(window)

    return AttrSpec(STANDARD_BUTTON_LABELS[2], KIND_BUTTON,
                    action=_action, tooltip=_TIP_APPLY)

def reset_plugin_defaults(plugin) -> None:
    plugin.system.reset()
    json_path = plugin.ensure_default_json()
    if json_path is not None:
        plugin.load_override_from(str(json_path))

def reset_button(window, plugin, after: Callable | None = None,
                 tooltip: str = _TIP_RESET) -> AttrSpec:
    def _action() -> None:
        reset_plugin_defaults(plugin)
        if after is not None:
            after()
        request_repaint(window)

    return AttrSpec(STANDARD_BUTTON_LABELS[3], KIND_BUTTON,
                    action=_action, tooltip=tooltip)

def console_button(window, plugin) -> AttrSpec:
    return AttrSpec(
        CONSOLE_BUTTON_LABEL, KIND_BUTTON,
        action=lambda: open_script_console(window, plugin),
        row_break=True, tooltip=_TIP_CONSOLE)

def standard_button_specs(window, plugin, add: Callable, remove: Callable,
                          add_tip: str = _TIP_SET_KEY,
                          del_tip: str = _TIP_DEL_KEY,
                          reset_tip: str = _TIP_RESET,
                          after: Callable | None = None) -> list:
    return keyframe_buttons(window, plugin, add, remove, add_tip, del_tip) + [
        apply_button(window, plugin, after),
        reset_button(window, plugin, after, reset_tip),
        console_button(window, plugin),
    ]

def bind_selected_key(window, key: str, handler: Callable,
                      flag: str) -> None:
    handlers = getattr(window, '_extra_handlers', None)
    if handlers is None:
        return
    prev = handlers.get(key)

    def _dispatch(win) -> None:
        if getattr(win, flag, False):
            handler(win)
            return
        if prev is not None:
            prev(win)

    handlers[key] = _dispatch
