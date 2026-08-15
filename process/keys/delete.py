import logging
from typing import Callable

from configs.settings import DELETE_DIALOG
from process.common.dialog import confirm

logger = logging.getLogger(__name__)

_DELETE_TITLE = 'Delete'
_DELETE_NOTE = 'Note: deleted items can be restored with Undo (Ctrl+Z).'

def _collect_targets(win) -> list[tuple[str, Callable[[], None]]]:
    providers = getattr(win, '_delete_providers', None)
    if not providers:
        return []
    targets: list[tuple[str, Callable[[], None]]] = []
    for provider in providers:
        descriptor = provider()
        if descriptor is not None:
            targets.append(descriptor)
    return targets

def handle_delete(win) -> None:
    targets = _collect_targets(win)
    if not targets:
        return
    if DELETE_DIALOG:
        labels = ', '.join(label for label, _ in targets)
        message = f'Delete {labels}?\n{_DELETE_NOTE}'
        if not confirm(win, _DELETE_TITLE, message):
            logger.info('Delete cancelled by user')
            return
    for _, delete in targets:
        delete()
