from process.common.widget import request_repaint
from process.objects.playback_select import (
    active_input_id, notify_pause_required, seek_to_input, selection_allowed,
)
from process.transform.attr_overlay import (
    activate_solo_selection, has_active_selection, reset_attr_overlay_if_idle,
)
from process.component.audio.display import display_label

def register_region_entry(window, label: str) -> None:
    def _provider() -> list:
        selected = (bool(getattr(window, '_audio_selected', False))
                    and not has_active_selection(window))

        return [(display_label(window, label), selected, True)]

    def _select(index: int) -> None:
        _toggle_selection(window)

    window._audio_list_provider = _provider
    window._audio_select_cb = _select

def register_audio_entries(window, entries: list[tuple[str, str]]) -> None:
    def _provider() -> list:

        active = (getattr(window, '_chain_active_iid', None)
                  or getattr(window, '_active_id', None))

        return [(label, iid == active, True) for iid, label in entries]

    def _select(index: int) -> None:

        if not (0 <= index < len(entries)):
            return
        iid = entries[index][0]
        if not selection_allowed(window, iid):
            notify_pause_required(window)
            return
        active = active_input_id(window)
        if active is None:
            active = getattr(window, '_active_id', None)
        if iid != active:
            seek_to_input(window, iid)
            _select_audio(window)
            return
        _toggle_selection(window)

    window._audio_list_provider = _provider
    window._audio_select_cb = _select

def _toggle_selection(window) -> None:

    shown = (getattr(window, '_audio_selected', False)
             and not has_active_selection(window))
    if not shown:
        _select_audio(window)
        return
    window._audio_selected = False
    reset_attr_overlay_if_idle(window)
    request_repaint(window)

def _select_audio(window) -> None:

    window._audio_selected = True
    activate_solo_selection(window, '_audio_selected')
    window._audio_selected = True
    widget = getattr(window, '_widget', None)
    if widget is not None:
        widget._attr_overlay_hidden = False
    request_repaint(window)
