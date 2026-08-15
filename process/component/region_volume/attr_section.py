import logging
from typing import Callable

from process.transform.attr_overlay import attr_solo_active
from process.widget.overlays import AttrSection
from process.component.region_volume.attr_common import (
    keyframe_button_specs, script_console_spec,
)
from process.component.region_volume.registry import get_registry

logger = logging.getLogger(__name__)

def _is_active_member(window, plugin) -> bool:
    if attr_solo_active(window):
        return False
    itc = getattr(window, '_input_transform', None)
    if itc is not None and itc.selected_id is not None:
        return False
    reg = get_registry(window)
    if reg is not None and plugin not in reg.members:
        return False
    if (reg is not None and reg.count() > 1
            and not reg.is_active_selection(plugin)):
        return False
    return True

def panel_owner(window):
    reg = get_registry(window)
    if reg is None:
        return None
    for member in reg.members:
        if _is_active_member(window, member):
            return member
    return None

def _register_keyframe_buttons(window, plugin) -> None:
    buttons = getattr(window, '_attr_keyframe_buttons', None)
    if buttons is None:
        buttons = []
        window._attr_keyframe_buttons = buttons

    def _provider():
        if not _is_active_member(window, plugin):
            return []
        return keyframe_button_specs(window, plugin)

    buttons.append(_provider)

def _register_console_button(window, plugin) -> None:
    buttons = getattr(window, '_attr_keyframe_buttons', None)
    if buttons is None:
        buttons = []
        window._attr_keyframe_buttons = buttons

    def _provider():
        if not _is_active_member(window, plugin):
            return []
        return [script_console_spec(window, plugin)]

    buttons.append(_provider)

def _restore_attr_overrides(window, plugin, build_specs) -> None:
    plugin.restore_pending_attrs(build_specs)

def _register_duration_listener(window, plugin) -> None:
    animator = getattr(plugin, 'keyframe_animator', None)
    if animator is None or not hasattr(animator, 'set_duration_ms'):
        return
    listeners = getattr(window, '_duration_listeners', None)
    if listeners is None:
        listeners = []
        window._duration_listeners = listeners
    listeners.append(animator.set_duration_ms)
    annot = getattr(window, '_annot_animator', None)
    if annot is not None:
        animator.set_duration_ms(annot.duration_ms)

def register_box_attr_section(
    window, plugin, title: str,
    build_specs: Callable[[], list],
    active: Callable[[], bool] | None = None,
) -> None:
    sections = getattr(window, '_attr_sections', None)
    if sections is None:
        return

    def _provider():
        if not _is_active_member(window, plugin):
            return None
        specs = build_specs()
        return specs or None

    sections.append(AttrSection(title, _provider))
    _register_keyframe_buttons(window, plugin)
    _register_console_button(window, plugin)
    _register_duration_listener(window, plugin)
    _restore_attr_overrides(window, plugin, build_specs)
    logger.debug('Attr section registered: %s', title)
