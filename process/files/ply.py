import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_CHUNK_BYTES: int = 8 * 1024 * 1024
_SH_BANDS: int = 16

_PLY_DTYPE_MAP: dict[str, type] = {
    'float': np.float32,
    'float32': np.float32,
    'double': np.float64,
    'uchar': np.uint8,
    'uint8': np.uint8,
    'int': np.int32,
    'short': np.int16,
}

def _parse_ply_header(
    f,
) -> tuple[int, list[tuple[str, type]]]:
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

def read_ply_body(
    f, total: int, on_progress: Callable[[float], None] | None = None,
) -> bytes:
    if on_progress is None or total <= 0:
        return f.read(max(total, 0))
    parts: list[bytes] = []
    loaded = 0
    while loaded < total:
        chunk = f.read(min(_CHUNK_BYTES, total - loaded))
        if not chunk:
            break
        parts.append(chunk)
        loaded += len(chunk)
        on_progress(loaded / total)
    return b''.join(parts)

def load_ply_raw(
    ply_path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    with open(ply_path, 'rb') as f:
        n_verts, props = _parse_ply_header(f)
        dtype = np.dtype(props)
        total = n_verts * dtype.itemsize
        binary = read_ply_body(f, total, on_progress)
    raw = np.frombuffer(binary, dtype=dtype)

    means_np = np.column_stack(
        [raw['x'], raw['y'], raw['z']]
    ).astype(np.float32)
    log_scales_np = np.column_stack(
        [raw['scale_0'], raw['scale_1'], raw['scale_2']]
    ).astype(np.float32)
    quats_np = np.column_stack(
        [raw['rot_0'], raw['rot_1'], raw['rot_2'], raw['rot_3']]
    ).astype(np.float32)
    opacity_logit = raw['opacity'].copy().astype(np.float32)

    sh_dc = np.column_stack(
        [raw['f_dc_0'], raw['f_dc_1'], raw['f_dc_2']]
    )
    rest_keys = sorted(
        [k for k in raw.dtype.names if k.startswith('f_rest_')],
        key=lambda k: int(k.split('_')[-1]),
    )
    sh_coeffs = np.zeros((n_verts, _SH_BANDS, 3), dtype=np.float32)
    sh_coeffs[:, 0, :] = sh_dc
    if rest_keys:
        f_rest = np.column_stack([raw[k] for k in rest_keys])
        n_bands = len(rest_keys) // 3
        sh_rest = f_rest.reshape(
            n_verts, 3, n_bands
        ).transpose(0, 2, 1)
        n_use = min(n_bands, _SH_BANDS - 1)
        sh_coeffs[:, 1:1 + n_use, :] = sh_rest[:, :n_use, :]

    logger.debug('Loaded %s: %d gaussians', ply_path.name, n_verts)
    return {
        'means_np': means_np,
        'log_scales_np': log_scales_np,
        'quats_np': quats_np,
        'opacity_logit': opacity_logit,
        'sh_coeffs': sh_coeffs,
    }
