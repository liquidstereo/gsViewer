import logging
from typing import Callable

from process.common.widget import request_repaint
from process.data.pointcloud_caps import notify_if_unsupported
from process.component.region_volume.keys import show_message_overlay
from process.component.region_volume.registry import get_registry
from process.component.region_volume.settings import REGION_VOLUME_NUM_KEYS

logger = logging.getLogger(__name__)

def _make_press_dispatch(key: str):
    def _dispatch(win) -> None:
        handler = get_registry(win).handler_for(key)
        if handler is not None:

            notify_if_unsupported(win, handler)
            handler(win)
    return _dispatch

def _make_release_dispatch(key: str):
    def _dispatch(win) -> None:
        handler = get_registry(win).release_handler_for(key)
        if handler is not None:
            handler(win)
    return _dispatch

def _select_via_channel(win, index: int) -> bool:

    cb = getattr(win, '_region_select_cb', None)
    provider = getattr(win, '_region_list_provider', None)
    if not (callable(cb) and callable(provider)):
        return False
    n = len(provider())

    if not (0 <= index < n):
        return True
    cb(index)
    return True

def _make_select_dispatch(index: int):
    def _dispatch(win) -> None:
        if _select_via_channel(win, index):
            return

        reg = get_registry(win)
        if reg.count() <= 1:
            return
        if not (0 <= index < reg.count()):
            return
        ctrl = reg.members[index]

        ctrl.on_select()
        if not reg.is_selected(ctrl):
            return
        label = getattr(ctrl, 'overlay_label', '') or 'REGION'
        vis = getattr(ctrl, 'is_visible', None)
        hidden = callable(vis) and not vis()
        suffix = ' (hidden, press H)' if hidden else ''
        show_message_overlay(win, f'SELECTED: {label}{suffix}')
        logger.info('RegionVolume selected: %s', label)
        request_repaint(win)
    return _dispatch

def bind_key(
    window, plugin, key: str, handler: Callable,
    allow_when_hidden: bool = False,
) -> None:
    reg = get_registry(window)
    first = reg.bind_handler(key, plugin, handler, allow_when_hidden)
    eh = getattr(window, '_extra_handlers', None)
    if first and eh is not None:
        eh[key] = _make_press_dispatch(key)

def bind_release_key(
    window, plugin, key: str, handler: Callable,
    allow_when_hidden: bool = False,
) -> None:
    reg = get_registry(window)
    first = reg.bind_release_handler(key, plugin, handler, allow_when_hidden)
    rh = getattr(window, '_extra_release_handlers', None)
    if first and rh is not None:
        rh[key] = _make_release_dispatch(key)

def bind_num_keys(window) -> None:
    eh = getattr(window, '_extra_handlers', None)
    if eh is None:
        return
    reg = get_registry(window)
    if reg._num_bound:
        return
    reg._num_bound = True
    for i, key in enumerate(REGION_VOLUME_NUM_KEYS):
        eh[key] = _make_select_dispatch(i)
