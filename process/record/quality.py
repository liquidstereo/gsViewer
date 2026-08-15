import logging

from configs.settings import SAVE_EXT
from process.record.settings import (
    QUALITY_PRESETS, QUALITY_FORCE_CODEC, VIDEO_PRESET_MAP, PNG_QUALITY_MAP,
)

logger = logging.getLogger(__name__)

def validate_save_args(
    fmt: str | None, quality: str | None, has_save: bool,
) -> str | None:
    if (fmt or quality) and not has_save:
        return ('-f/--format and -q/--quality require a save flag '
                '(-s/-ss/-sq)')
    if quality is None or quality in QUALITY_PRESETS:
        return None
    resolved = (fmt or SAVE_EXT).lower()
    if resolved == 'png' and quality.isdigit() and 0 <= int(quality) <= 100:
        return None
    return ('-q/--quality must be one of low/medium/high/raw '
            '(png also accepts an integer 0-100)')

def video_codec_override(
    quality: str | None,
) -> tuple[str | None, list[str] | None]:
    if quality not in VIDEO_PRESET_MAP:
        return None, None
    args = ['-preset', VIDEO_PRESET_MAP[quality], '-pix_fmt', 'yuv420p']
    return QUALITY_FORCE_CODEC, args

def png_quality_value(quality: str | None, default: int) -> int:
    if quality is None:
        return default
    if quality in PNG_QUALITY_MAP:
        return PNG_QUALITY_MAP[quality]
    return int(quality)
