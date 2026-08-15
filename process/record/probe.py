import logging
import shutil
import subprocess

from process.record.settings import (
    FFMPEG_BIN, VIDEO_CODEC, NVENC_CODEC, SW_CODEC, CODEC_ARGS,
)

logger = logging.getLogger(__name__)

def ffmpeg_available() -> bool:
    return shutil.which(FFMPEG_BIN) is not None

def _list_encoders() -> str:
    try:
        out = subprocess.run(
            [FFMPEG_BIN, '-hide_banner', '-encoders'],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning('ffmpeg encoder probe failed: %s', exc)
        return ''

def nvenc_available() -> bool:
    return NVENC_CODEC in _list_encoders()

def select_codec() -> str:
    if VIDEO_CODEC == 'auto':
        return NVENC_CODEC if nvenc_available() else SW_CODEC
    if VIDEO_CODEC not in CODEC_ARGS:
        logger.warning(
            'Unknown VIDEO_CODEC=%s, fallback to %s',
            VIDEO_CODEC, SW_CODEC,
        )
        return SW_CODEC
    return VIDEO_CODEC
