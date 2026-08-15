import logging
from pathlib import Path

import numpy as np

from utils.structures import GaussianBuffer

logger = logging.getLogger(__name__)

def _build_ply_header(n: int, n_rest: int) -> bytes:
    lines = [
        'ply',
        'format binary_little_endian 1.0',
        f'element vertex {n}',
        'property float x',
        'property float y',
        'property float z',
        'property float f_dc_0',
        'property float f_dc_1',
        'property float f_dc_2',
    ]
    for i in range(n_rest):
        lines.append(f'property float f_rest_{i}')
    lines += [
        'property float opacity',
        'property float scale_0',
        'property float scale_1',
        'property float scale_2',
        'property float rot_0',
        'property float rot_1',
        'property float rot_2',
        'property float rot_3',
        'end_header',
        '',
    ]
    return '\n'.join(lines).encode('ascii')

def _build_dtype(n_rest: int) -> np.dtype:
    parts = [
        ('x', np.float32), ('y', np.float32), ('z', np.float32),
        ('f_dc_0', np.float32), ('f_dc_1', np.float32), ('f_dc_2', np.float32),
    ]
    for i in range(n_rest):
        parts.append((f'f_rest_{i}', np.float32))
    parts += [
        ('opacity', np.float32),
        ('scale_0', np.float32), ('scale_1', np.float32), ('scale_2', np.float32),
        ('rot_0', np.float32), ('rot_1', np.float32),
        ('rot_2', np.float32), ('rot_3', np.float32),
    ]
    return np.dtype(parts)

def _fill_sh_rest(out: np.ndarray, buf: GaussianBuffer, n_rest: int) -> None:
    if n_rest == 0 or buf.sh_coeffs is None or buf.sh_coeffs.shape[1] <= 1:
        return
    sh_rest = buf.sh_coeffs[:, 1:, :]
    f_rest = sh_rest.transpose(0, 2, 1).reshape(len(out), n_rest)
    for i in range(n_rest):
        out[f'f_rest_{i}'] = f_rest[:, i]

def encode_ply(buf: GaussianBuffer, path: Path) -> None:
    if buf.means is None or buf.sh_coeffs is None:
        raise ValueError('GaussianBuffer is missing required fields')

    n = buf.n_gaussians
    k = buf.sh_coeffs.shape[1]
    n_rest = (k - 1) * 3

    dtype = _build_dtype(n_rest)
    out = np.zeros(n, dtype=dtype)

    out['x'] = buf.means[:, 0]
    out['y'] = buf.means[:, 1]
    out['z'] = buf.means[:, 2]
    out['f_dc_0'] = buf.sh_coeffs[:, 0, 0]
    out['f_dc_1'] = buf.sh_coeffs[:, 0, 1]
    out['f_dc_2'] = buf.sh_coeffs[:, 0, 2]
    _fill_sh_rest(out, buf, n_rest)
    out['opacity'] = buf.opacity
    out['scale_0'] = buf.scales[:, 0]
    out['scale_1'] = buf.scales[:, 1]
    out['scale_2'] = buf.scales[:, 2]
    out['rot_0'] = buf.rotations[:, 0]
    out['rot_1'] = buf.rotations[:, 1]
    out['rot_2'] = buf.rotations[:, 2]
    out['rot_3'] = buf.rotations[:, 3]

    header = _build_ply_header(n, n_rest)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(header)
        f.write(out.tobytes())
    logger.info('Encoded PLY: %d gaussians -> %s', n, path.name)
