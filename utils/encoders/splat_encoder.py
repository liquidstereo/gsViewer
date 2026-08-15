import logging
from pathlib import Path

import numpy as np

from utils.structures import GaussianBuffer

logger = logging.getLogger(__name__)

_C0: float = 0.28209479177387814

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

def _sh_dc_to_rgb_u8(sh_dc: np.ndarray) -> np.ndarray:
    rgb = sh_dc * _C0 + 0.5
    return np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)

def _opacity_to_alpha_u8(logit: np.ndarray) -> np.ndarray:
    p = 1.0 / (1.0 + np.exp(-logit.astype(np.float32)))
    return np.clip(np.round(p * 255.0), 0, 255).astype(np.uint8)

def _wxyz_to_xyzw_i8(wxyz: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(wxyz, axis=1, keepdims=True)
    norm = np.where(norm < 0.00000001, 1.0, norm)
    n = wxyz / norm
    xyzw = n[:, [1, 2, 3, 0]]
    return np.clip(np.round(xyzw * 127.5), -128, 127).astype(np.int8)

def encode_splat(buf: GaussianBuffer, path: Path) -> None:
    if buf.means is None or buf.sh_coeffs is None:
        raise ValueError('GaussianBuffer is missing required fields')

    n = buf.n_gaussians
    out = np.zeros(n, dtype=_SPLAT_DTYPE)

    out['x'] = buf.means[:, 0]
    out['y'] = buf.means[:, 1]
    out['z'] = buf.means[:, 2]

    exp_scales = np.exp(buf.scales)
    out['scale_x'] = exp_scales[:, 0]
    out['scale_y'] = exp_scales[:, 1]
    out['scale_z'] = exp_scales[:, 2]

    rgb_u8 = _sh_dc_to_rgb_u8(buf.sh_coeffs[:, 0, :])
    out['r'] = rgb_u8[:, 0]
    out['g'] = rgb_u8[:, 1]
    out['b'] = rgb_u8[:, 2]
    out['a'] = _opacity_to_alpha_u8(buf.opacity)

    rot_i8 = _wxyz_to_xyzw_i8(buf.rotations)
    out['rot_x'] = rot_i8[:, 0]
    out['rot_y'] = rot_i8[:, 1]
    out['rot_z'] = rot_i8[:, 2]
    out['rot_w'] = rot_i8[:, 3]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.tobytes())
    logger.info('Encoded .splat: %d gaussians -> %s', n, path.name)
