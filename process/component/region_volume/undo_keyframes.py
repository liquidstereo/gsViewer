import logging

from process.common.widget import request_repaint

logger = logging.getLogger(__name__)

def snapshot_keyframes(kf) -> list[dict]:
    return kf.snapshot()

def _keyframes_changed(a: list[dict], b: list[dict]) -> bool:
    return len(a) != len(b)

def record_keyframes(
    window, plugin, before: list[dict], after: list[dict], label: str,
) -> None:
    stack = getattr(window, '_undo_stack', None)
    if stack is None or not _keyframes_changed(before, after):
        return

    def restore(items: list[dict]) -> None:
        kf = plugin.keyframes
        kf.set_items(items)
        kf.save(plugin.keyframes_path)
        request_repaint(window)

    stack.push(label, lambda: restore(before), lambda: restore(after))
