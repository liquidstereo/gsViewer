import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np

from process.files._dequant import logit_from_u8, quat_normalize_safe

logger = logging.getLogger(__name__)

_SH_RANGE: float = 2.0
_SH_FULL: float = _SH_RANGE * 2.0
_SH_BANDS: int = 16

_PLY_DTYPE_MAP: dict[str, type] = {
    'float':   np.float32,
    'float32': np.float32,
    'double':  np.float64,
    'uchar':   np.uint8,
    'uint8':   np.uint8,
    'int':     np.int32,
    'short':   np.int16,
}

def _parse_header(f) -> tuple[int, list[tuple[str, type]]]:
    assert f.readline().decode('ascii').strip() == 'ply'
    n_verts = 0
    props: list[tuple[str, type]] = []
    for line in iter(
        lambda: f.readline().decode('ascii').strip(),
        'end_header',
    ):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'element' and parts[1] == 'vertex':
            n_verts = int(parts[2])
        elif parts[0] == 'property' and len(parts) == 3:
            dtype = _PLY_DTYPE_MAP.get(parts[1], np.float32)
            props.append((parts[2], dtype))
    return n_verts, props

def _dequant_sh(u8: np.ndarray) -> np.ndarray:
    return (u8.astype(np.float32) / 255.0 * _SH_FULL - _SH_RANGE)

def _dequant_opacity(u8: np.ndarray) -> np.ndarray:
    return logit_from_u8(u8)

def _dequant_rotation(u8: np.ndarray) -> np.ndarray:
    raw = u8.astype(np.float32) / 255.0 * 2.0 - 1.0
    return quat_normalize_safe(raw)

def _extract_sh(
    raw: np.ndarray, n: int, prop_names: list[str]
) -> np.ndarray:
    sh_dc = _dequant_sh(np.column_stack(
        [raw['f_dc_0'], raw['f_dc_1'], raw['f_dc_2']]
    ))
    rest_keys = sorted(
        [k for k in prop_names if k.startswith('f_rest_')],
        key=lambda k: int(k.split('_')[-1]),
    )
    sh_coeffs = np.zeros((n, _SH_BANDS, 3), dtype=np.float32)
    sh_coeffs[:, 0, :] = sh_dc
    if not rest_keys:
        return sh_coeffs
    f_rest = _dequant_sh(
        np.column_stack([raw[k] for k in rest_keys])
    )
    n_bands = len(rest_keys) // 3
    sh_rest = f_rest.reshape(n, 3, n_bands).transpose(0, 2, 1)
    n_use = min(n_bands, _SH_BANDS - 1)
    sh_coeffs[:, 1:1 + n_use, :] = sh_rest[:, :n_use, :]
    return sh_coeffs

def load_cply_frame(
    path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    with open(path, 'rb') as f:
        n, props = _parse_header(f)
        dtype = np.dtype(props)
        raw = np.frombuffer(f.read(), dtype=dtype)
    if on_progress is not None:
        on_progress(0.5)

    prop_names = [p[0] for p in props]
    means_np = np.column_stack(
        [raw['x'], raw['y'], raw['z']]
    ).astype(np.float32)
    log_scales_np = np.column_stack(
        [raw['scale_0'], raw['scale_1'], raw['scale_2']]
    ).astype(np.float32)
    quats_np = _dequant_rotation(np.column_stack(
        [raw['rot_0'], raw['rot_1'], raw['rot_2'], raw['rot_3']]
    ))
    opacity_logit = _dequant_opacity(raw['opacity'])
    sh_coeffs = _extract_sh(raw, n, prop_names)
    if on_progress is not None:
        on_progress(1.0)

    logger.debug('Loaded cply: %d gaussians from %s', n, path.name)
    return {
        'means_np':      means_np,
        'log_scales_np': log_scales_np,
        'quats_np':      quats_np,
        'opacity_logit': opacity_logit,
        'sh_coeffs':     sh_coeffs,
    }
