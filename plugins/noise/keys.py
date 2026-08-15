import logging

from process.common.cycle import cycle_next
from process.common.widget import request_repaint
from plugins.noise.settings import (
    NOISE_NOISE_TYPES, NOISE_THRESHOLD_STEP,
)
from process.component.region_volume.keys import show_message_overlay
from process.component.region_volume.registry import get_registry

logger = logging.getLogger(__name__)

def _get_plugin(win):

    sel = get_registry(win).selected()
    if sel is not None and getattr(sel, '_base_label', None) == 'NOISE':
        return sel
    return getattr(win, '_noise_plugin', None)

def handle_toggle_noise(win) -> None:
    p = _get_plugin(win)
    if p is None:
        return
    p.system.toggle_active()
    state = 'ON' if p.system.active else 'OFF'
    show_message_overlay(win, f'NOISE {state}')
    request_repaint(win)

def handle_cycle_noise_type(win) -> None:
    p = _get_plugin(win)
    if p is None:
        return
    nxt = cycle_next(NOISE_NOISE_TYPES, p.system.noise_type)
    p.system.noise_type = nxt
    show_message_overlay(win, f'NOISE TYPE: {nxt}')
    logger.info('Noise type: %s', nxt)
    request_repaint(win)

def _nudge_threshold(win, delta: float) -> None:
    p = _get_plugin(win)
    if p is None:
        return
    value = p.system.adjust_threshold(delta)
    show_message_overlay(win, f'NOISE: {value:.2f}')
    request_repaint(win)

def handle_threshold_up(win) -> None:
    _nudge_threshold(win, NOISE_THRESHOLD_STEP)

def handle_threshold_down(win) -> None:
    _nudge_threshold(win, -NOISE_THRESHOLD_STEP)
