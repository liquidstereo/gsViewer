import json
import logging
import zipfile
from pathlib import Path

from process.files.ply import _parse_ply_header

logger = logging.getLogger(__name__)

_SPLAT_STRIDE: int = 32

def peek_gaussian_count(path: Path) -> int:
    suffix = path.suffix.lower()
    try:
        if path.name.endswith('.compressed.ply') or suffix == '.ply':
            return _peek_ply(path)
        if suffix == '.sog':
            return _peek_sog(path)
        if suffix == '.splat':
            return path.stat().st_size // _SPLAT_STRIDE
    except Exception:
        logger.debug('peek_gaussian_count failed: %s', path.name)
    return 0

def _peek_ply(path: Path) -> int:
    with open(path, 'rb') as f:
        n, _ = _parse_ply_header(f)
    return n

def _peek_sog(path: Path) -> int:
    with zipfile.ZipFile(path, 'r') as z:
        meta = json.loads(z.read('meta.json'))
    return int(meta['count'])
