import logging

from process.common.widget import request_repaint
from process.component.region_volume.keys import show_message_overlay
from process.component.region_volume.registry import get_registry

logger = logging.getLogger(__name__)

def _get_plugin(win):

    sel = get_registry(win).selected()
    if sel is not None and getattr(sel, '_base_label', None) == 'CROP':
        return sel
    return getattr(win, '_crop_plugin', None)

def handle_toggle_crop(win) -> None:
    p = _get_plugin(win)
    if p is None:
        return
    p.system.toggle_active()
    state = 'ON' if p.system.active else 'OFF'
    show_message_overlay(win, f'CROP {state}')
    request_repaint(win)

def handle_toggle_invert(win) -> None:
    p = _get_plugin(win)
    if p is None:
        return
    p.system.toggle_invert()
    state = 'OUTSIDE' if p.system.invert else 'INSIDE'
    show_message_overlay(win, f'CROP KEEP: {state}')
    request_repaint(win)
