import logging

from configs.keybinding import SOLO_TOGGLE, TOGGLE_CORNER_BRACKET
from process.console import open_script_console
from process.cursor.menu_actions import apply_reset
from process.keys.effects import handle_toggle_plugin_help
from process.component.region_volume.solo import toggle_region_solo
from process.component.region_volume.settings import (
    REGION_VOLUME_KEY_ATTR, REGION_VOLUME_KEY_CONSOLE,
    REGION_VOLUME_KEY_HELP, REGION_VOLUME_KEY_LOCK, REGION_VOLUME_KEY_RESET,
    REGION_VOLUME_KEY_TOOL_ROTATE, REGION_VOLUME_KEY_TOOL_SCALE,
    REGION_VOLUME_KEY_TOOL_TRANSLATE, REGION_VOLUME_KEY_VISIBLE,
    TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
)

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
    key = getattr(plugin, 'effect_key', '') or ''
    return (label, _toggle, key)

def _region_context_items(window, plugin) -> list:
    def _render() -> None:
        fn = getattr(window, '_render_current', None)
        if fn is not None:
            fn()
        elif hasattr(window, '_widget'):
            window._widget.update()

    def _set_tool(mode: str) -> None:
        plugin.region_visible = True
        plugin.tool_mode = mode
        _render()

    def _toggle_visible() -> None:
        plugin.region_visible = not plugin.region_visible
        _render()

    def _reset() -> None:

        apply_reset(window, plugin)
        _render()

    def _toggle_lock() -> None:
        fn = getattr(plugin, 'toggle_region_lock', None)
        if fn is not None:
            fn()
        _render()

    def _toggle_help() -> None:
        handle_toggle_plugin_help(window)

    def _open_console() -> None:
        open_script_console(window, plugin)

    def _select() -> None:
        plugin.on_select()
        _render()

    def _toggle_bracket_mode() -> None:
        plugin.bracket_mode = not getattr(plugin, 'bracket_mode', False)
        _render()

    def _solo() -> None:
        toggle_region_solo(window, plugin)

    reg = getattr(window, '_region_volume_registry', None)
    solo_label = (
        'unsolo' if reg is not None and reg.is_soloed(plugin) else 'solo')
    locked = bool(getattr(plugin, 'region_locked', False))
    lock_label = 'unlock' if locked else 'lock'
    bracket_label = (
        'Display Full' if getattr(plugin, 'bracket_mode', False)
        else 'Display as Bracket')
    items: list = [('select', _select, REGION_VOLUME_KEY_ATTR)]
    effect = _effect_item(plugin, _render)
    if effect is not None:
        items.append(effect)
    items.append((solo_label, _solo, SOLO_TOGGLE))
    vis_label = 'hide' if plugin.region_visible else 'show'
    items.extend([
        ('translate', lambda: _set_tool(TOOL_TRANSLATE),
         REGION_VOLUME_KEY_TOOL_TRANSLATE),
        ('rotate', lambda: _set_tool(TOOL_ROTATE),
         REGION_VOLUME_KEY_TOOL_ROTATE),
        ('scale', lambda: _set_tool(TOOL_SCALE),
         REGION_VOLUME_KEY_TOOL_SCALE),
        (lock_label, _toggle_lock, REGION_VOLUME_KEY_LOCK),
        (vis_label, _toggle_visible, REGION_VOLUME_KEY_VISIBLE),
        ('reset', _reset, REGION_VOLUME_KEY_RESET),
        (bracket_label, _toggle_bracket_mode, TOGGLE_CORNER_BRACKET),
        ('open with script console', _open_console, REGION_VOLUME_KEY_CONSOLE),
        ('help', _toggle_help, REGION_VOLUME_KEY_HELP),
    ])
    return items

def _make_provider(window, plugin):
    def provider() -> list:
        target = getattr(plugin, 'target', None)
        if target is None:
            return []

        label = getattr(plugin, 'overlay_label', '') or 'REGION'
        return [('region', label, _region_context_items(window, plugin))]
    return provider

def register_region_context(window, plugin) -> None:
    targets = getattr(window, '_cursor_menu_targets', None)
    if targets is None:
        targets = []
        window._cursor_menu_targets = targets
    targets.append(_make_provider(window, plugin))
