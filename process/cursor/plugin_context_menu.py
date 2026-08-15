import logging

from configs.keybinding import TOGGLE_PLUGIN_HELP
from process.console import open_script_console
from process.cursor.menu_actions import apply_reset, has_reset
from process.keys.effects import handle_toggle_plugin_help

logger = logging.getLogger(__name__)

def _effect_item(plugin, render):

    is_active = getattr(plugin, 'is_effect_active', None)
    toggle = getattr(plugin, 'toggle_effect_active', None)
    if not callable(is_active) or not callable(toggle):
        return None

    def _toggle() -> None:
        toggle()
        render()

    label = 'deactivate' if is_active() else 'activate'
    return (label, _toggle, getattr(plugin, 'effect_key', '') or '')

def _reset_item(window, plugin, render):
    if not has_reset(plugin):
        return None

    def _reset() -> None:
        apply_reset(window, plugin)
        render()

    return ('reset', _reset)

def _console_item(window, plugin):
    if not callable(getattr(plugin, 'settings_module_path', None)):
        return None
    return ('open with script console',
            lambda: open_script_console(window, plugin))

def plugin_context_items(window, plugin) -> list:
    def _render() -> None:
        fn = getattr(window, '_render_current', None)
        if fn is not None:
            fn()
        elif hasattr(window, '_widget'):
            window._widget.update()

    def _select() -> None:
        plugin.on_select()
        _render()

    items: list = [('select', _select)]
    for build in (_effect_item(plugin, _render),
                  _reset_item(window, plugin, _render),
                  _console_item(window, plugin)):
        if build is not None:
            items.append(build)
    items.append(('help', lambda: handle_toggle_plugin_help(window),
                  TOGGLE_PLUGIN_HELP))
    return items

def register_plugin_context(window, plugin) -> None:
    targets = getattr(window, '_cursor_menu_targets', None)
    if targets is None:
        targets = []
        window._cursor_menu_targets = targets

    def provider() -> list:
        label = getattr(plugin, 'overlay_label', '') or 'PLUGIN'
        return [('region', label, plugin_context_items(window, plugin))]

    targets.append(provider)
