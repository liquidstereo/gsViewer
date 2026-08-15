import logging
from pathlib import Path

import numpy as np

from utils.structures import GaussianBuffer

logger = logging.getLogger(__name__)

_SH_RANGE: float = 2.0
_SH_FULL: float = _SH_RANGE * 2.0

def _quant_sh(x: np.ndarray) -> np.ndarray:
    q = (np.clip(x, -_SH_RANGE, _SH_RANGE) + _SH_RANGE) / _SH_FULL * 255.0
    return np.clip(np.round(q), 0, 255).astype(np.uint8)

def _quant_opacity(logit: np.ndarray) -> np.ndarray:
    p = 1.0 / (1.0 + np.exp(-logit.astype(np.float32)))
    return np.clip(np.round(p * 255.0), 0, 255).astype(np.uint8)

def _quant_rotation(wxyz: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(wxyz, axis=1, keepdims=True)
    norm = np.where(norm < 0.00000001, 1.0, norm)
    n = wxyz / norm
    q = np.clip(np.round((n + 1.0) / 2.0 * 255.0), 0, 255)
    return q.astype(np.uint8)

def _build_cply_header(n: int, n_rest: int) -> bytes:
    lines = [
        'ply',
        'format binary_little_endian 1.0',
        f'element vertex {n}',
        'property float x',
        'property float y',
        'property float z',
        'property float scale_0',
        'property float scale_1',
        'property float scale_2',
        'property uchar f_dc_0',
        'property uchar f_dc_1',
        'property uchar f_dc_2',
        'property uchar opacity',
        'property uchar rot_0',
        'property uchar rot_1',
        'property uchar rot_2',
        'property uchar rot_3',
    ]
    for i in range(n_rest):
        lines.append(f'property uchar f_rest_{i}')
    lines += ['end_header', '']
    return '\n'.join(lines).encode('ascii')

def _build_cply_dtype(n_rest: int) -> np.dtype:
    parts = [
        ('x', np.float32), ('y', np.float32), ('z', np.float32),
        ('scale_0', np.float32), ('scale_1', np.float32), ('scale_2', np.float32),
        ('f_dc_0', np.uint8), ('f_dc_1', np.uint8), ('f_dc_2', np.uint8),
        ('opacity', np.uint8),
        ('rot_0', np.uint8), ('rot_1', np.uint8),
        ('rot_2', np.uint8), ('rot_3', np.uint8),
    ]
    for i in range(n_rest):
        parts.append((f'f_rest_{i}', np.uint8))
    return np.dtype(parts)

def _fill_sh_rest_cply(
    out: np.ndarray, buf: GaussianBuffer, n_rest: int
) -> None:
    if n_rest == 0 or buf.sh_coeffs is None or buf.sh_coeffs.shape[1] <= 1:
        return
    sh_rest = buf.sh_coeffs[:, 1:, :]
    f_rest = sh_rest.transpose(0, 2, 1).reshape(len(out), n_rest)
    f_rest_q = _quant_sh(f_rest)
    for i in range(n_rest):
        out[f'f_rest_{i}'] = f_rest_q[:, i]

def encode_cply(buf: GaussianBuffer, path: Path) -> None:
    if buf.means is None or buf.sh_coeffs is None:
        raise ValueError('GaussianBuffer is missing required fields')

    n = buf.n_gaussians
    k = buf.sh_coeffs.shape[1]
    n_rest = (k - 1) * 3

    dtype = _build_cply_dtype(n_rest)
    out = np.zeros(n, dtype=dtype)

    out['x'] = buf.means[:, 0]
    out['y'] = buf.means[:, 1]
    out['z'] = buf.means[:, 2]
    out['scale_0'] = buf.scales[:, 0]
    out['scale_1'] = buf.scales[:, 1]
    out['scale_2'] = buf.scales[:, 2]

    sh_dc_q = _quant_sh(buf.sh_coeffs[:, 0, :])
    out['f_dc_0'] = sh_dc_q[:, 0]
    out['f_dc_1'] = sh_dc_q[:, 1]
    out['f_dc_2'] = sh_dc_q[:, 2]
    out['opacity'] = _quant_opacity(buf.opacity)

    rot_q = _quant_rotation(buf.rotations)
    out['rot_0'] = rot_q[:, 0]
    out['rot_1'] = rot_q[:, 1]
    out['rot_2'] = rot_q[:, 2]
    out['rot_3'] = rot_q[:, 3]
    _fill_sh_rest_cply(out, buf, n_rest)

    header = _build_cply_header(n, n_rest)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(header)
        f.write(out.tobytes())
    logger.info('Encoded cply: %d gaussians -> %s', n, path.name)
