import logging
import os
from collections.abc import Callable
from pathlib import Path

from configs.colorize import Msg
from configs.settings import CACHE_FLUSH_TIMEOUT
from process.common import truncate_string

logger = logging.getLogger(__name__)

def force_exit(
    input_name: str,
    log_path: Path | None,
    files_count: int,
    msg_fn: Callable[..., None] | None = None,
    text: str | None = None,
    close_fn: Callable[[], None] | None = None,
    extra_note: str | None = None,
) -> None:
    if msg_fn is None:
        msg_fn = Msg.Result
    if text is None:
        text = f'Playback For "{input_name}" finished.'
    suffix = f' ({files_count} Files)' if files_count > 1 else ''
    msg_fn(f'{text}{suffix}', divide=False)
    if extra_note:
        Msg.Dim(extra_note)
    if log_path:
        Msg.Dim(
            f'Please refer to the log file for details.'
            f' ({truncate_string(log_path, 60)})'
        )
    try:
        if close_fn is not None:
            close_fn()
    finally:
        from process.data.cache import flush_pending_caches
        flush_pending_caches(CACHE_FLUSH_TIMEOUT)
        logging.shutdown()
        os._exit(0)
