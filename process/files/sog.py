import io
import json
import logging
import zipfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_SH_BANDS: int = 16
_NORM: float = float(np.sqrt(2))
_MODE_OFFSET: int = 252

def _read_webp(z: zipfile.ZipFile, name: str) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(z.read(name))), dtype=np.uint8)

def _decode_means(
    arr_l: np.ndarray,
    arr_u: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray,
    n: int,
) -> np.ndarray:
    lower = arr_l.reshape(-1, 4)[:n, :3].astype(np.float32)
    upper = arr_u.reshape(-1, 4)[:n, :3].astype(np.float32)
    combined = (upper * 256.0 + lower) / 65535.0
    nx = (combined * (maxs - mins) + mins).astype(np.float32)
    return (np.sign(nx) * (np.exp(np.abs(nx)) - 1.0)).astype(np.float32)

def _decode_quats(arr: np.ndarray, n: int) -> np.ndarray:
    raw = arr.reshape(-1, 4)[:n]
    a = (raw[:, 0].astype(np.float32) / 255.0 - 0.5) * _NORM
    b = (raw[:, 1].astype(np.float32) / 255.0 - 0.5) * _NORM
    c = (raw[:, 2].astype(np.float32) / 255.0 - 0.5) * _NORM
    d = np.sqrt(np.maximum(0.0, 1.0 - a * a - b * b - c * c))
    mode = raw[:, 3].astype(np.int32) - _MODE_OFFSET

    xyzw = np.empty((n, 4), dtype=np.float32)
    for m, cols in enumerate([
        (a, b, c, d),
        (d, b, c, a),
        (b, d, c, a),
        (b, c, d, a),
    ]):
        mask = mode == m
        if mask.any():
            xyzw[mask] = np.stack(
                [col[mask] for col in cols], axis=1
            )

    wxyz = xyzw[:, [3, 0, 1, 2]]
    norm = np.linalg.norm(wxyz, axis=1, keepdims=True)
    norm = np.where(norm < 0.00000001, 1.0, norm)
    return (wxyz / norm).astype(np.float32)

def _decode_codebook(
    arr: np.ndarray, codebook: np.ndarray, n: int, ch: int = 3,
) -> np.ndarray:
    indices = arr.reshape(-1, 4)[:n, :ch].astype(np.uint8)
    return codebook[indices].astype(np.float32)

def load_sog_frame(
    path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    with zipfile.ZipFile(path, 'r') as z:
        meta = json.loads(z.read('meta.json'))
        n: int = meta['count']

        mins = np.array(meta['means']['mins'], dtype=np.float32)
        maxs = np.array(meta['means']['maxs'], dtype=np.float32)
        means_np = _decode_means(
            _read_webp(z, 'means_l.webp'),
            _read_webp(z, 'means_u.webp'),
            mins, maxs, n,
        )
        if on_progress is not None:
            on_progress(0.45)

        sc_cb = np.array(meta['scales']['codebook'], dtype=np.float32)
        log_scales_np = _decode_codebook(
            _read_webp(z, 'scales.webp'), sc_cb, n,
        )
        if on_progress is not None:
            on_progress(0.60)

        quats_np = _decode_quats(_read_webp(z, 'quats.webp'), n)
        if on_progress is not None:
            on_progress(0.85)

        sh_cb = np.array(meta['sh0']['codebook'], dtype=np.float32)
        sh0_arr = _read_webp(z, 'sh0.webp').reshape(-1, 4)[:n]
        sh0 = sh_cb[sh0_arr[:, :3].astype(np.uint8)]
        sh_coeffs = np.zeros((n, _SH_BANDS, 3), dtype=np.float32)
        sh_coeffs[:, 0, :] = sh0.astype(np.float32)
        opacity_logit = sh_cb[sh0_arr[:, 3].astype(np.uint8)]
        if on_progress is not None:
            on_progress(1.0)

    logger.debug('Loaded %s: %d gaussians', path.name, n)
    return {
        'means_np':      means_np,
        'log_scales_np': log_scales_np,
        'quats_np':      quats_np,
        'opacity_logit': opacity_logit,
        'sh_coeffs':     sh_coeffs,
    }
