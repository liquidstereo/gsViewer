import logging

from process.common.widget import request_repaint
from process.data.source_gate import restore_disabled_rows
from process.widget.overlays import AttrSpec
from process.widget.overlays.attr_spec import KIND_ENUM

logger = logging.getLogger(__name__)

def gateable_plugins(window) -> list:
    out = []
    for plugin in getattr(window, '_plugins', []) or []:
        if (hasattr(plugin, '_process_frame')
                and getattr(plugin, 'overlay_label', None)):
            out.append(plugin)
    return out

def _state(window) -> dict:
    st = getattr(window, '_object_plugin_state', None)
    if st is None:
        st = {}
        window._object_plugin_state = st
    return st

def is_enabled(window, input_key: str, label: str) -> bool:
    return _state(window).get(input_key, {}).get(label, True)

def set_enabled(window, input_key: str, label: str, value: bool) -> None:
    _state(window).setdefault(input_key, {})[label] = bool(value)

def _disabled_indices(window, label: str) -> set:

    splat = getattr(window, '_splat', None)
    keys = splat.get('_source_keys') if splat else None
    if not keys:
        return set()
    st = _state(window)
    return {
        i for i, key in enumerate(keys)
        if not st.get(key, {}).get(label, True)
    }

def _make_gate(window, plugin, base_proc):
    label = plugin.overlay_label

    def _gated(splat: dict) -> dict:
        out = base_proc(splat)
        return restore_disabled_rows(
            splat, out, _disabled_indices(window, label))
    return _gated

def install_object_plugin_gates(window) -> None:
    procs = getattr(window, '_frame_processors', None)
    if procs is None:
        return
    gateable = {id(p) for p in gateable_plugins(window)}
    count = 0
    for i, proc in enumerate(procs):
        plugin = getattr(proc, '_gate_plugin', None)
        if plugin is None or id(plugin) not in gateable:
            continue
        if getattr(proc, '_object_gated', False):
            continue
        gate = _make_gate(window, plugin, proc)
        gate._gate_plugin = plugin
        gate._object_gated = True
        procs[i] = gate
        count += 1
    logger.debug('Object plugin gates installed (%d/%d plugins)',
                 count, len(gateable))

def apply_plugin_specs(window, controller) -> list:
    plugins = gateable_plugins(window)
    if not plugins:
        return []

    def _all_on() -> bool:
        sid = controller.selected_id
        return sid is not None and all(
            is_enabled(window, sid, p.overlay_label) for p in plugins)

    def _summary() -> str:
        sid = controller.selected_id
        if sid is None:
            return ''
        on = sum(1 for p in plugins
                 if is_enabled(window, sid, p.overlay_label))
        total = len(plugins)
        if on == total:
            return 'All'
        return 'None' if on == 0 else f'{on}/{total}'

    def _items() -> list:
        sid = controller.selected_id
        if sid is None:
            return []
        items = [('All', _all_on())]
        for p in plugins:
            items.append(
                (p.overlay_label, is_enabled(window, sid, p.overlay_label)))
        return items

    def _toggle(text: str) -> None:
        sid = controller.selected_id
        if sid is None:
            return
        if text == 'All':
            value = not _all_on()
            for p in plugins:
                set_enabled(window, sid, p.overlay_label, value)
        else:
            set_enabled(window, sid, text, not is_enabled(window, sid, text))
        request_repaint(window)

    width_opts = tuple(['All'] + [p.overlay_label for p in plugins])
    return [AttrSpec(
        'Apply Plugins', KIND_ENUM, get=_summary, set=lambda v: None,
        options=width_opts, menu_provider=_items, menu_toggle=_toggle,
        tooltip='Apply each plugin to this object (per-object on/off).')]
