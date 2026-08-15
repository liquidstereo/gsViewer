import logging
from typing import Callable

from PySide6.QtWidgets import QInputDialog, QLineEdit

from configs.settings import ENABLE_INSTANT_JSON_SYNC
from process.common.widget import request_repaint
from process.component.region_volume.keys import show_message_overlay
from process.component.region_volume.undo_keyframes import (
    record_keyframes, snapshot_keyframes,
)
from process.widget.text_case import keep_case

logger = logging.getLogger(__name__)

def _repaint(win) -> None:
    request_repaint(win)

def _region_name(plugin) -> str:

    return getattr(plugin, 'overlay_label', 'Region Volume').title()

def _apply_state(plugin, item: dict) -> None:
    apply_extra = getattr(plugin, 'apply_keyframe_extra', None)
    if callable(apply_extra):
        apply_extra(item.get('extra', {}) or {})
    animator = getattr(plugin, 'keyframe_animator', None)
    if animator is not None:
        animator.start(item)
        return
    region = plugin.region
    region.center = item['center'].copy()
    region.size = item['size'].copy()
    region.rotation = item['rotation'].copy()
    region.softness = float(item['softness'])
    set_scalar = getattr(plugin, 'on_scalar_update', None)
    if callable(set_scalar):
        for key, val in (item.get('scalars', {}) or {}).items():
            set_scalar(key, val)
    plugin.save_region()

def make_add_keyframe(plugin) -> Callable:
    def handler(win) -> None:
        kf = plugin.keyframes
        name = _region_name(plugin)
        default = f'{name} Keyframe {kf.count() + 1}'
        label, ok = QInputDialog.getText(
            win,
            f'Add {name} Keyframe',
            'Label:',
            QLineEdit.EchoMode.Normal,
            default,
        )
        if not ok or not label.strip():
            return
        capture_extra = getattr(plugin, 'keyframe_extra', None)
        extra = capture_extra() if callable(capture_extra) else None
        capture_scalars = getattr(plugin, 'keyframe_scalars', None)
        scalars = (
            capture_scalars() if callable(capture_scalars) else None
        )
        before = snapshot_keyframes(kf)
        kf.add(
            plugin.region.center, plugin.region.size,
            plugin.region.rotation, plugin.region.softness,
            label.strip(), extra=extra, scalars=scalars,
        )
        if ENABLE_INSTANT_JSON_SYNC:
            kf.save(plugin.keyframes_path)
        record_keyframes(
            win, plugin, before, snapshot_keyframes(kf), 'Keyframe add',
        )
        show_message_overlay(
            win,
            f'{name} Keyframe Added: {keep_case(label.strip())}',
        )
        _repaint(win)
    return handler

def make_remove_keyframe(plugin) -> Callable:
    def handler(win) -> None:
        kf = plugin.keyframes
        name = _region_name(plugin)
        before = snapshot_keyframes(kf)
        if kf.remove_last():
            kf.save(plugin.keyframes_path)
            record_keyframes(
                win, plugin, before, snapshot_keyframes(kf),
                'Keyframe remove',
            )
            show_message_overlay(win, f'{name} KEY Removed.')
            _repaint(win)
        else:
            logger.warning('No region_volume keyframes to remove')
    return handler

def make_clear_keyframes(plugin) -> Callable:
    def handler(win) -> None:
        kf = plugin.keyframes
        name = _region_name(plugin)
        if kf.count() == 0:
            logger.warning('No region_volume keyframes to clear')
            return
        animator = getattr(plugin, 'keyframe_animator', None)
        if animator is not None:
            animator.stop()
        before = snapshot_keyframes(kf)
        kf.clear()
        kf.save(plugin.keyframes_path)
        record_keyframes(
            win, plugin, before, snapshot_keyframes(kf), 'Keyframe clear',
        )
        delete_curves = getattr(plugin, 'delete_curves', None)
        if callable(delete_curves):
            delete_curves()
        show_message_overlay(win, f'{name} KEYS Cleared.')
        logger.info('All region_volume keyframes cleared')
        _repaint(win)
    return handler

def make_toggle_keyframes(plugin) -> Callable:
    def handler(win) -> None:
        name = _region_name(plugin)
        plugin.keyframes_visible = not plugin.keyframes_visible
        state = 'On' if plugin.keyframes_visible else 'Off'
        show_message_overlay(win, f'{name} KEYS {state}.')
        logger.info('RegionVolume keyframes overlay: %s', state)
        _repaint(win)
    return handler

def make_goto_keyframe(plugin, delta: int) -> Callable:
    def handler(win) -> None:
        kf = plugin.keyframes
        item = kf.goto(delta)
        if item is None:
            return
        _apply_state(plugin, item)
        name = _region_name(plugin)
        n = kf.count()
        idx = kf.cursor()
        show_message_overlay(
            win,
            f'{name} KEY [{idx + 1}/{n}]: '
            f'{keep_case(item["label"])}',
        )
        logger.info(
            'Goto region_volume keyframe [%d/%d]: %r',
            idx + 1, n, item['label'],
        )
        _repaint(win)
    return handler
