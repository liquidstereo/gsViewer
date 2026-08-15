import logging

from process.common.widget import request_repaint

logger = logging.getLogger(__name__)

def snapshot_reset_state(plugin) -> dict:
    return {
        'override': plugin._build_override_data(),
        'visible': bool(getattr(plugin, 'region_visible', False)),
        'locked': bool(getattr(plugin, 'region_locked', False)),
    }

def _reset_changed(a: dict, b: dict) -> bool:
    return (a['override'] != b['override']
            or a['visible'] != b['visible']
            or a['locked'] != b['locked'])

def record_reset(
    window, plugin, before: dict, after: dict, label: str,
) -> None:
    stack = getattr(window, '_undo_stack', None)
    if stack is None or not _reset_changed(before, after):
        return

    def restore(snap: dict, drop_json: bool) -> None:
        plugin.apply_override_data(snap['override'])
        plugin.region_visible = snap['visible']
        plugin.region_locked = snap['locked']
        if drop_json:
            plugin.region.delete_file(plugin.region_path)
        request_repaint(window)

    stack.push(label,
               lambda: restore(before, False),
               lambda: restore(after, True))
