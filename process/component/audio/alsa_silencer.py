import ctypes
import logging

logger = logging.getLogger(__name__)

_ERR_HANDLER_FUNC_TYPE = ctypes.CFUNCTYPE(
    None,
    ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
    ctypes.c_int, ctypes.c_char_p,
)

_installed: bool = False

_handler_ref: object | None = None

def _silent_handler(filename, line, function, err, fmt) -> None:
    return

def install_alsa_silencer() -> bool:
    global _installed, _handler_ref
    if _installed:
        return True
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    except OSError as e:
        logger.debug('ALSA silencer unavailable: %s', e)
        return False
    try:
        _handler_ref = _ERR_HANDLER_FUNC_TYPE(_silent_handler)
        asound.snd_lib_error_set_handler(_handler_ref)
        _installed = True
        logger.info('ALSA error handler silenced')
        return True
    except (OSError, AttributeError) as e:
        logger.warning('ALSA silencer install failed: %s', e)
        return False
