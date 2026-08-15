import logging
import os
import signal
import sys
import threading

import psutil

from configs.settings import (
    CONSOLE_LOG,
    LOG_FILE_LEVEL, LOG_FORMAT, LOG_MSEC_FORMAT, LOG_OVERLAY_LEVEL,
    LOGS_DIR, PROJECT_ROOT,
)
from configs.settings_overlay import LOG_OVERLAY_MAX_LINES
from process.common.widget import set_message_overlay as _set_message_overlay
from process.widget.text_case import strip_keep_case

logger = logging.getLogger(__name__)

_MAX_LOG_LINES: int = LOG_OVERLAY_MAX_LINES
_recent_logs: list[tuple[int, str]] = []

_last_alert: tuple[int, str] = (0, '')

_ROOT_PREFIX: str = f'{PROJECT_ROOT}{os.sep}'

_LEVEL_PREFIX: dict[int, str] = {
    logging.WARNING: 'WARN ',
    logging.ERROR: 'ERROR ',
    logging.CRITICAL: 'CRITICAL ',
}

def _to_rel_paths(message: str) -> str:
    return message.replace(_ROOT_PREFIX, '')

class _MemoryLogHandler(logging.Handler):

    def emit(self, record: logging.LogRecord) -> None:

        overlay_flag = getattr(record, 'overlay', None)
        if overlay_flag is False:
            return
        show = record.levelno >= logging.INFO or overlay_flag is True
        if not show:
            return
        prefix = _LEVEL_PREFIX.get(record.levelno, '')
        message = _to_rel_paths(record.getMessage())
        text = f'{prefix}{strip_keep_case(message)}'

        if record.levelno >= logging.WARNING:
            _set_alert(getattr(record, 'alert', '') or message)
        entry = (record.levelno, text)
        if entry in _recent_logs:
            return
        _recent_logs.append(entry)
        if len(_recent_logs) > _MAX_LOG_LINES:
            _recent_logs.pop(0)

class _DedupFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self._seen: set[tuple] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.WARNING:
            return True
        key = (record.name, record.lineno, record.getMessage())
        if key in self._seen:
            return False
        self._seen.add(key)
        return True

def get_recent_logs() -> list[tuple[int, str]]:
    return list(_recent_logs)

def _set_alert(text: str) -> None:

    global _last_alert
    _last_alert = (_last_alert[0] + 1, text)

def get_last_alert() -> tuple[int, str]:
    return _last_alert

def overlay_log(
    logger_obj: logging.Logger, message: str, *args: object
) -> None:
    logger_obj.debug(message, *args, extra={'overlay': True})

def format_event(
    target: str, action: str, attr: str | None = None,
    value: object = None,
) -> str:
    parts = [target]
    if attr:
        parts.append(attr)
    parts.append(action)
    msg = '.'.join(parts)
    if value is not None and value != '':
        msg = f'{msg}: {value}'
    return msg

def overlay_event(
    logger_obj: logging.Logger, target: str, action: str,
    attr: str | None = None, value: object = None,
    to_file: bool = False,
) -> None:
    msg = format_event(target, action, attr, value)
    if to_file:
        logger_obj.info('%s', msg)
    else:
        logger_obj.debug('%s', msg, extra={'overlay': True})

def set_message_overlay(win, text: str) -> None:
    _set_message_overlay(win, text)

def start_shutdown_blink() -> tuple[threading.Thread, threading.Event]:
    from configs.colorize import Msg
    from configs.settings import (
        SHUTDOWN_BLINK_MESSAGE, SHUTDOWN_BLINK_INTERVAL,
        SHUTDOWN_BLINK_COLOR,
    )
    stop = threading.Event()
    thread = threading.Thread(
        target=Msg.Blink,
        kwargs={
            'message': SHUTDOWN_BLINK_MESSAGE,
            'interval': SHUTDOWN_BLINK_INTERVAL,
            'color': SHUTDOWN_BLINK_COLOR,
            'stop_event': stop,
            'clear_on_finish': True,
        },
        daemon=True,
    )
    thread.start()
    return thread, stop

def stop_shutdown_blink(
    thread: threading.Thread, stop: threading.Event,
) -> None:
    from configs.settings import SHUTDOWN_BLINK_JOIN_TIMEOUT
    stop.set()
    thread.join(timeout=SHUTDOWN_BLINK_JOIN_TIMEOUT)

def kill_child_workers() -> None:
    try:
        parent = psutil.Process(os.getpid())
        for child in parent.children(recursive=True):
            child.kill()
        logger.info('child workers killed')
    except Exception:
        logger.warning('kill_child_workers failed', exc_info=True)

def _level_from_name(name: str, default: int) -> int:

    level = logging.getLevelName(name.strip().upper())
    return level if isinstance(level, int) else default

def setup_logging(log_name: str, verbose: bool = False) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    file_level = (
        logging.DEBUG if verbose
        else _level_from_name(LOG_FILE_LEVEL, logging.INFO)
    )
    overlay_level = _level_from_name(LOG_OVERLAY_LEVEL, logging.DEBUG)
    handler = logging.FileHandler(
        LOGS_DIR / f'{log_name}.log', mode='w', encoding='utf-8'
    )
    fmt = logging.Formatter(LOG_FORMAT)
    fmt.default_msec_format = LOG_MSEC_FORMAT
    handler.setFormatter(fmt)
    handler.addFilter(_DedupFilter())
    handler.setLevel(file_level)
    mem = _MemoryLogHandler()
    mem.setLevel(overlay_level)
    root = logging.getLogger()
    root.addHandler(handler)
    root.addHandler(mem)
    if CONSOLE_LOG:

        con = logging.StreamHandler(sys.stdout)
        con.setFormatter(fmt)
        con.addFilter(_DedupFilter())
        con.setLevel(logging.DEBUG if verbose else logging.INFO)
        root.addHandler(con)
    root.setLevel(min(file_level, overlay_level))

def interrupt_exit() -> None:
    import sys
    sys.stdout = sys.__stdout__
    from configs.colorize import Msg
    Msg.Error('Gsviewer interrupted.', divide=False)
    kill_child_workers()
    logging.shutdown()
    os._exit(0)

def register_sigint_handler(on_interrupt=None) -> None:
    def _handler(sig, frame):
        if on_interrupt is not None:
            on_interrupt()
            return
        interrupt_exit()
    signal.signal(signal.SIGINT, _handler)
