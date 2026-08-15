import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_SH_BANDS: int = 16
_C0: float = 0.28209479177387814
_BYTES_PER_GAUSSIAN: int = 32

_SPLAT_DTYPE = np.dtype([
    ('x',       np.float32),
    ('y',       np.float32),
    ('z',       np.float32),
    ('scale_x', np.float32),
    ('scale_y', np.float32),
    ('scale_z', np.float32),
    ('r',       np.uint8),
    ('g',       np.uint8),
    ('b',       np.uint8),
    ('a',       np.uint8),
    ('rot_x',   np.int8),
    ('rot_y',   np.int8),
    ('rot_z',   np.int8),
    ('rot_w',   np.int8),
])

def _parse_splat_binary(raw: np.ndarray) -> dict:
    n = len(raw)

    means_np = np.column_stack(
        [raw['x'], raw['y'], raw['z']]
    ).astype(np.float32)

    scales = np.column_stack(
        [raw['scale_x'], raw['scale_y'], raw['scale_z']]
    ).astype(np.float32)
    log_scales_np = np.log(np.clip(scales, 0.00000001, None))

    xyzw = np.column_stack([
        raw['rot_x'].astype(np.float32) / 127.5,
        raw['rot_y'].astype(np.float32) / 127.5,
        raw['rot_z'].astype(np.float32) / 127.5,
        raw['rot_w'].astype(np.float32) / 127.5,
    ])
    norm = np.linalg.norm(xyzw, axis=1, keepdims=True)
    norm = np.where(norm < 0.00000001, 1.0, norm)
    xyzw = xyzw / norm
    quats_np = xyzw[:, [3, 0, 1, 2]]

    rgb = np.column_stack([
        raw['r'].astype(np.float32) / 255.0,
        raw['g'].astype(np.float32) / 255.0,
        raw['b'].astype(np.float32) / 255.0,
    ])
    sh_coeffs = np.zeros((n, _SH_BANDS, 3), dtype=np.float32)
    sh_coeffs[:, 0, :] = (rgb - 0.5) / _C0

    alpha = np.clip(
        raw['a'].astype(np.float32) / 255.0, 0.000001, 1.0 - 0.000001
    )
    opacity_logit = np.log(alpha / (1.0 - alpha)).astype(np.float32)

    return {
        'means_np':      means_np,
        'log_scales_np': log_scales_np,
        'quats_np':      quats_np,
        'opacity_logit': opacity_logit,
        'sh_coeffs':     sh_coeffs,
    }

def load_splat_frame(
    path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    data = path.read_bytes()
    remainder = len(data) % _BYTES_PER_GAUSSIAN
    if remainder != 0:
        raise ValueError(
            f'Invalid .splat file size: {len(data)} bytes '
            f'(expected multiple of {_BYTES_PER_GAUSSIAN})'
        )
    raw = np.frombuffer(data, dtype=_SPLAT_DTYPE)
    if on_progress is not None:
        on_progress(0.5)
    result = _parse_splat_binary(raw)
    if on_progress is not None:
        on_progress(1.0)
    logger.debug('Loaded %s: %d gaussians', path.name, len(raw))
    return result
