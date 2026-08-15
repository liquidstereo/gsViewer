import logging
from pathlib import Path

import numpy as np

from utils.structures import GaussianBuffer
from utils.decoders.ply_decoder import parse_ply_header, read_ply_binary

logger = logging.getLogger(__name__)

_SH_RANGE: float = 2.0
_SH_FULL: float = _SH_RANGE * 2.0

def _dequant_sh(u8: np.ndarray) -> np.ndarray:
    return (u8.astype(np.float32) / 255.0 * _SH_FULL - _SH_RANGE)

def _dequant_opacity(u8: np.ndarray) -> np.ndarray:
    p = np.clip(u8.astype(np.float32) / 255.0, 0.000001, 1.0 - 0.000001)
    return np.log(p / (1.0 - p)).astype(np.float32)

def _dequant_rotation(u8: np.ndarray) -> np.ndarray:
    raw = u8.astype(np.float32) / 255.0 * 2.0 - 1.0
    norm = np.linalg.norm(raw, axis=1, keepdims=True)
    norm = np.where(norm < 0.00000001, 1.0, norm)
    return (raw / norm).astype(np.float32)

def _extract_sh_cply(
    raw: np.ndarray, n: int, prop_names: list[str]
) -> np.ndarray:
    sh_dc = _dequant_sh(
        np.column_stack([raw['f_dc_0'], raw['f_dc_1'], raw['f_dc_2']])
    )
    rest_keys = sorted(
        [k for k in prop_names if k.startswith('f_rest_')],
        key=lambda k: int(k.split('_')[-1]),
    )
    if not rest_keys:
        return sh_dc[:, None, :]
    n_rest = len(rest_keys)
    f_rest_u8 = np.column_stack([raw[k] for k in rest_keys])
    f_rest = _dequant_sh(f_rest_u8)
    n_bands = n_rest // 3
    sh_rest = f_rest.reshape(n, 3, n_bands).transpose(0, 2, 1)
    return np.concatenate(
        [sh_dc[:, None, :], sh_rest], axis=1
    ).astype(np.float32)

def decode_cply(path: Path) -> GaussianBuffer:
    with open(path, 'rb') as f:
        n, props = parse_ply_header(f)
        dtype = np.dtype(props)
        raw = read_ply_binary(f, n, dtype)

    prop_names = [p[0] for p in props]
    means = np.column_stack(
        [raw['x'], raw['y'], raw['z']]
    ).astype(np.float32)
    scales = np.column_stack(
        [raw['scale_0'], raw['scale_1'], raw['scale_2']]
    ).astype(np.float32)
    rot_u8 = np.column_stack(
        [raw['rot_0'], raw['rot_1'], raw['rot_2'], raw['rot_3']]
    )
    rotations = _dequant_rotation(rot_u8)
    opacity = _dequant_opacity(raw['opacity'])
    sh_coeffs = _extract_sh_cply(raw, n, prop_names)

    logger.info('Decoded cply: %d gaussians from %s', n, path.name)
    return GaussianBuffer(
        means=means,
        rotations=rotations,
        scales=scales,
        opacity=opacity,
        sh_coeffs=sh_coeffs,
    )
