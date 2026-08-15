import logging
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QFileDialog

from process.common.attr_random import reset_window_attr_random
from process.common.widget import (
    request_repaint, set_message_overlay as _set_message_overlay,
)
from process.console import open_script_console
from process.handle import overlay_event
from process.undo import record_region_state, snapshot_region_state
from process.component.region_volume.solo import clear_region_solo
from process.component.region_volume.undo_reset import (
    record_reset, snapshot_reset_state,
)
from process.component.region_volume.settings import (
    REGION_VOLUME_STARTUP_VISIBILITY, REGION_VOLUME_STRENGTH_MAX,
    REGION_VOLUME_STRENGTH_MIN,
    TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE, VOLUME_SHAPES,
)

logger = logging.getLogger(__name__)

_TOOL_LABEL: dict[str, str] = {
    TOOL_TRANSLATE: 'TRANSLATE',
    TOOL_ROTATE:    'ROTATE',
    TOOL_SCALE:     'SCALE',
}

def _repaint(win) -> None:
    request_repaint(win)

def show_message_overlay(win, text: str) -> None:
    _set_message_overlay(win, text)

def make_toggle_visible(plugin) -> Callable:
    def handler(win) -> None:
        before = snapshot_region_state(plugin)
        plugin.region_visible = not plugin.region_visible
        after = snapshot_region_state(plugin)
        label = plugin.overlay_label or 'REGION'
        state = 'ON' if plugin.region_visible else 'OFF'
        show_message_overlay(win, f'{label} REGION: {state}')
        overlay_event(logger, f'Region({label})',
                      'Show' if plugin.region_visible else 'Hide',
                      to_file=True)
        record_region_state(win, plugin, before, after, f'Region {label} show')
        _repaint(win)
    return handler

def make_reset(plugin) -> Callable:
    def handler(win) -> None:
        animator = getattr(plugin, 'keyframe_animator', None)
        if animator is not None:
            animator.stop()
        plugin.region.reset()
        plugin.region.delete_file(plugin.region_path)
        delete_curves = getattr(plugin, 'delete_curves', None)
        if callable(delete_curves):
            delete_curves()
        hook = getattr(plugin, 'on_reset', None)
        if callable(hook):
            hook()
        overlay_event(logger, f'Region({plugin.overlay_label or "REGION"})',
                      'Reset', to_file=True)
        _repaint(win)
    return handler

def make_reset_to_default(plugin) -> Callable:
    base = make_reset(plugin)

    def handler(win) -> None:
        before = snapshot_reset_state(plugin)
        base(win)
        clear_region_solo(win)
        plugin.region_locked = False
        reset_window_attr_random(win)
        json_path = plugin.ensure_default_json()
        if json_path is not None:
            plugin.load_override_from(str(json_path))
        plugin.region_visible = REGION_VOLUME_STARTUP_VISIBILITY
        after = snapshot_reset_state(plugin)
        label = plugin.overlay_label or 'REGION'
        record_reset(win, plugin, before, after, f'Region {label} reset')
        _repaint(win)
    return handler

def _preset_dir(plugin) -> str:
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

def make_apply_override(plugin) -> Callable:
    def handler(win) -> None:
        start = _preset_dir(plugin)
        path, _ = QFileDialog.getOpenFileName(
            win, 'Apply JSON Settings', start, 'JSON (*.json)')
        if not path:
            return
        plugin.load_override_from(path)
        overlay_event(logger, f'Region({plugin.overlay_label or "REGION"})',
                      'Apply', attr='Settings', to_file=True)
        _repaint(win)
    return handler

def make_toggle_lock(plugin) -> Callable:
    def handler(win) -> None:
        before = snapshot_region_state(plugin)
        locked = plugin.toggle_region_lock()
        after = snapshot_region_state(plugin)
        label = plugin.overlay_label or 'REGION'
        overlay_event(logger, f'Region({label})',
                      'Lock' if locked else 'Unlock', to_file=True)
        record_region_state(win, plugin, before, after, f'Region {label} lock')
        _repaint(win)
    return handler

def make_adjust_strength(plugin, delta: float) -> Callable:
    def handler(win) -> None:
        system = getattr(plugin, 'system', None)
        if system is None or not hasattr(system, 'strength_scale'):
            return
        value = system.strength_scale + delta
        value = max(REGION_VOLUME_STRENGTH_MIN,
                    min(REGION_VOLUME_STRENGTH_MAX, value))
        system.strength_scale = value
        label = plugin.overlay_label or 'REGION'
        show_message_overlay(win, f'{label} STRENGTH: {value:.1f}x')
        overlay_event(logger, f'Region({label})', 'Update',
                      attr='Strength', value=f'{value:.2f}', to_file=True)
        _repaint(win)
    return handler

def make_set_tool(plugin, tool: str) -> Callable:
    def handler(win) -> None:
        if plugin.tool_mode == tool:
            return
        plugin.tool_mode = tool
        label = _TOOL_LABEL.get(tool)
        if label is not None:
            show_message_overlay(win, label)
        overlay_event(
            logger,
            f'Region({plugin.overlay_label or "region_volume"})',
            'Update', attr='Tool', value=tool, to_file=True)
        _repaint(win)
    return handler

def make_cycle_shape(plugin) -> Callable:
    def handler(win) -> None:
        shapes = VOLUME_SHAPES
        if not shapes:
            return
        cur = getattr(plugin, 'shape', shapes[0])
        idx = shapes.index(cur) if cur in shapes else 0
        nxt = shapes[(idx + 1) % len(shapes)]
        plugin.rebuild_region(nxt)
        show_message_overlay(win, f'SHAPE: {nxt.upper()}')
        _repaint(win)
    return handler

def make_open_console(plugin) -> Callable:
    def handler(win) -> None:
        open_script_console(win, plugin)
    return handler

def make_show_attr(plugin) -> Callable:
    def handler(win) -> None:
        plugin.on_select()
        _repaint(win)
    return handler
