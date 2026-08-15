import logging
import sys
from pathlib import Path

from configs.colorize import Msg
from process.common.resource_lookup import resolve_named_resource
from process.component.audio.settings import AUDIO_DIR, AUDIO_AUTO_EXTS

logger = logging.getLogger(__name__)

def resolve_audio_path(raw: str | None) -> str | None:
    if raw is None:
        return None
    p = Path(raw)
    if p.exists():
        return str(p)
    candidate = AUDIO_DIR / raw
    if candidate.exists():
        return str(candidate)
    Msg.Error(f'Audio not found: "{raw}"', divide=False)
    sys.exit(1)

def primary_audio_path(raw: str | list[str] | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return next((item for item in raw if item), None)
    items = [s.strip() for s in raw.split(',') if s.strip()]
    if not items:
        return None
    return resolve_audio_path(items[0])

def auto_detect_audio_path(input_name: str) -> str | None:
    p = resolve_named_resource(AUDIO_DIR, input_name, AUDIO_AUTO_EXTS)
    if p is None or not p.is_file():
        return None
    logger.info('Audio auto-detected for "%s": %s', input_name, p)
    return str(p)
