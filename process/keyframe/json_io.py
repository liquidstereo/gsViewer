import json
import logging
from pathlib import Path
from typing import Any

from process.common.floatfmt import dumps_fixed

_logger = logging.getLogger(__name__)

def write_keyframe_json(
    path: Path, data: Any, label: str,
    log: logging.Logger | None = None,
    count: int | None = None,
    log_removed: bool = False,
) -> None:
    out = log or _logger
    if not data:
        if path.exists():
            path.unlink()
            if log_removed:
                out.info('%s keyframes file removed: %s', label, path.name)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        dumps_fixed(data, indent=2, ensure_ascii=False), encoding='utf-8')
    if count is None:
        out.info('%s keyframes saved: %s', label, path.name)
        return
    out.info('%s keyframes saved: %s (%d items)', label, path.name, count)

def read_keyframe_json(
    path: Path, label: str, log: logging.Logger | None = None,
) -> Any | None:
    out = log or _logger
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        out.warning('%s keyframes load failed: %s', label, e)
        return None
