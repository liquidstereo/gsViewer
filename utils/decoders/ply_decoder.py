import logging
from pathlib import Path
from typing import BinaryIO

import numpy as np

from utils.structures import GaussianBuffer

logger = logging.getLogger(__name__)

_CHUNK_BYTES: int = 8 * 1024 * 1024

PLY_DTYPE_MAP: dict[str, type] = {
    'float': np.float32,
    'float32': np.float32,
    'double': np.float64,
    'uchar': np.uint8,
    'uint8': np.uint8,
    'int': np.int32,
    'short': np.int16,
    'ushort': np.uint16,
}

def parse_ply_header(f: BinaryIO) -> tuple[int, list[tuple[str, type]]]:
    assert f.readline().decode('ascii').strip() == 'ply'
    n_verts = 0
    props: list[tuple[str, type]] = []
    for line in iter(
        lambda: f.readline().decode('ascii').strip(), 'end_header'
    ):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'element' and parts[1] == 'vertex':
            n_verts = int(parts[2])
        elif parts[0] == 'property' and len(parts) == 3:
            dtype = PLY_DTYPE_MAP.get(parts[1], np.float32)
            props.append((parts[2], dtype))
    return n_verts, props

def read_ply_binary(f: BinaryIO, n: int, dtype: np.dtype) -> np.ndarray:
    total = n * dtype.itemsize
    parts: list[bytes] = []
    loaded = 0
    while loaded < total:
        chunk = f.read(min(_CHUNK_BYTES, total - loaded))
        if not chunk:
            break
        parts.append(chunk)
        loaded += len(chunk)
    return np.frombuffer(b''.join(parts), dtype=dtype)

def _extract_sh(
    raw: np.ndarray, n: int, prop_names: list[str]
) -> np.ndarray:
    sh_dc = np.column_stack(
        [raw['f_dc_0'], raw['f_dc_1'], raw['f_dc_2']]
    ).astype(np.float32)
    rest_keys = sorted(
        [k for k in prop_names if k.startswith('f_rest_')],
        key=lambda k: int(k.split('_')[-1]),
    )
    if not rest_keys:
        return sh_dc[:, None, :]
    n_rest = len(rest_keys)
    f_rest = np.column_stack(
        [raw[k] for k in rest_keys]
    ).astype(np.float32)
    n_bands = n_rest // 3
    sh_rest = f_rest.reshape(n, 3, n_bands).transpose(0, 2, 1)
    return np.concatenate(
        [sh_dc[:, None, :], sh_rest], axis=1
    ).astype(np.float32)

def decode_ply(path: Path) -> GaussianBuffer:
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
    rotations = np.column_stack(
        [raw['rot_0'], raw['rot_1'], raw['rot_2'], raw['rot_3']]
    ).astype(np.float32)
    opacity = raw['opacity'].astype(np.float32)
    sh_coeffs = _extract_sh(raw, n, prop_names)

    logger.info('Decoded PLY: %d gaussians from %s', n, path.name)
    return GaussianBuffer(
        means=means,
        rotations=rotations,
        scales=scales,
        opacity=opacity,
        sh_coeffs=sh_coeffs,
    )
