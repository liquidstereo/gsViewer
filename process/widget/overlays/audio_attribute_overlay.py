from typing import Callable

from configs.settings_overlay import STARTUP_AUDIO_ATTRIBUTE_OVERLAY
from process.common.widget import request_repaint
from process.component.region_volume.attr_section import panel_owner
from process.transform.attr_overlay import (
    attr_solo_active, has_active_selection)
from process.widget.overlays.attr_spec import (
    AttrSection, AttrSpec, KIND_BOOL,
)

_TIP_SHOW_AUDIO = 'Show the audio equalizer box in this panel.'
_SOLO_FLAG_SUFFIX = '_selected'

def show_audio_key(owner) -> str:
    if isinstance(owner, str):
        return owner.upper().replace(' ', '')
    label = getattr(owner, 'overlay_label', None) or type(owner).__name__
    return str(label).upper().replace(' ', '')

def solo_flag_key(flag: str) -> str:
    name = flag[1:] if flag.startswith('_') else flag
    if name.endswith(_SOLO_FLAG_SUFFIX):
        name = name[:-len(_SOLO_FLAG_SUFFIX)]
    return show_audio_key(name)

def show_audio_enabled(window, key: str) -> bool:
    states = getattr(window, '_audio_ui_visible_map', None)
    if not states or not key:
        return False
    return bool(states.get(key, False))

def set_show_audio(window, owner, value: bool) -> None:
    states = getattr(window, '_audio_ui_visible_map', None)
    if states is None:
        states = {}
        window._audio_ui_visible_map = states
    states[show_audio_key(owner)] = bool(value)

def current_show_audio_owner(window) -> str | None:
    owner = panel_owner(window)
    if owner is not None:
        return show_audio_key(owner)
    if has_active_selection(window):

        return None
    for flag in getattr(window, '_attr_solo_flags', ()):
        if getattr(window, flag, False):
            return solo_flag_key(flag)
    return None

def init_audio_attribute_overlay_state(window) -> None:
    window._audio_selected = bool(STARTUP_AUDIO_ATTRIBUTE_OVERLAY)

    window._audio_ui_visible_map = {}

def register_audio_attribute_overlay(
    window, title: str | Callable[[], str], solo_specs, merged_specs,
    meta_specs, order: int,
) -> None:
    sections = getattr(window, '_attr_sections', None)
    if sections is None:
        return

    def _provider():
        active = has_active_selection(window)

        if not active:
            if getattr(window, '_audio_selected', False):
                return solo_specs()

            if (attr_solo_active(window, '_audio_selected')
                    and show_audio_enabled(
                        window, current_show_audio_owner(window))):
                return meta_specs()

            if show_audio_enabled(window, current_show_audio_owner(window)):
                return merged_specs()
            return None

        if show_audio_enabled(window, current_show_audio_owner(window)):
            return merged_specs()
        return None

    sections.append(AttrSection(title, _provider, order=order))

def make_show_audio_spec(window, owner) -> AttrSpec:
    key = show_audio_key(owner)

    def _set(value: bool) -> None:
        set_show_audio(window, key, value)
        request_repaint(window)

    return AttrSpec(
        'Show Audio', KIND_BOOL,
        lambda: show_audio_enabled(window, key), _set,
        default=False, tooltip=_TIP_SHOW_AUDIO)

def make_show_audio_provider(window):
    def _provider(box_window, box_plugin) -> list:
        return [make_show_audio_spec(window, box_plugin)]

    return _provider
