import logging

from process.common.dialog import confirm
from process.reset.core import reset_all

logger = logging.getLogger(__name__)

_RESET_TITLE = 'Reset All'
_RESET_TEXT = (

    'Delete all saved states and reset to defaults?\n'
    'Warn: This action cannot be undone.'
)

def _confirm(win) -> bool:
    return confirm(win, _RESET_TITLE, _RESET_TEXT)

def handle_reset_all(win) -> None:
    if not _confirm(win):
        logger.info('Reset cancelled by user')
        return
    reset_all(win)
