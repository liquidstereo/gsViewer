import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np

from configs.settings_glpoints import (
    GAUSSIAN_PROPERTY_PREFIXES, PLY_HEADER_PROBE_BYTES,
    POINTCLOUD_COLOR_KEYS, POINTCLOUD_COLOR_UINT8_SCALE,
    POINTCLOUD_DEFAULT_COLOR,
)
from process.common import hex_to_rgb
from process.data.cache import (
    _KIND_POINTCLOUD, load_cached_pointcloud, save_cache_async,
)
from process.files.ply import _parse_ply_header, read_ply_body

logger = logging.getLogger(__name__)

_XYZ_KEYS: tuple[str, str, str] = ('x', 'y', 'z')

def _has_ply_header(ply_path: Path) -> bool:

    with open(ply_path, 'rb') as f:
        head = f.read(PLY_HEADER_PROBE_BYTES)
    return head.startswith(b'ply') and b'end_header' in head

def _read_props(ply_path: Path) -> list[tuple[str, type]]:
    with open(ply_path, 'rb') as f:
        _, props = _parse_ply_header(f)
    return props

def is_pure_point_cloud(ply_path: Path) -> bool:
    path = Path(ply_path)
    if not path.is_file() or not _has_ply_header(path):

        if path.suffix.lower() == '.ply':
            logger.warning('Not a readable PLY header: %s', path.name)
        else:
            logger.debug('Not a PLY container, skipping point cloud '
                         'probe: %s', path.name)
        return False
    names = [name for name, _ in _read_props(path)]
    if not all(key in names for key in _XYZ_KEYS):
        logger.warning('PLY without x/y/z vertex properties: %s',
                       path.name)
        return False
    return not any(
        name.startswith(prefix)
        for name in names
        for prefix in GAUSSIAN_PROPERTY_PREFIXES
    )

def _default_colors(count: int) -> np.ndarray:
    rgb = np.array(hex_to_rgb(POINTCLOUD_DEFAULT_COLOR), dtype=np.float32)
    return np.tile(rgb, (count, 1))

def _extract_colors(raw: np.ndarray, count: int) -> np.ndarray:
    names = raw.dtype.names or ()
    for keys in POINTCLOUD_COLOR_KEYS:
        if not all(key in names for key in keys):
            continue
        channels = np.column_stack([raw[key] for key in keys])
        if np.issubdtype(channels.dtype, np.integer):
            channels = (
                channels.astype(np.float32) / POINTCLOUD_COLOR_UINT8_SCALE
            )
        return np.ascontiguousarray(
            channels.astype(np.float32).clip(0.0, 1.0)
        )
    return _default_colors(count)

def load_point_cloud(
    ply_path: Path, use_cache: bool = True,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    path = Path(ply_path)
    if use_cache:
        cached = load_cached_pointcloud(path)
        if cached is not None:
            return cached
    if not _has_ply_header(path):
        raise ValueError(f'Not a PLY file (no header): {path.name}')
    with open(path, 'rb') as f:
        n_verts, props = _parse_ply_header(f)
        dtype = np.dtype(props)
        expected = n_verts * dtype.itemsize
        binary = read_ply_body(f, expected, on_progress)
    names = [name for name, _ in props]
    missing = [key for key in _XYZ_KEYS if key not in names]
    if missing:
        raise ValueError(
            f'PLY without vertex properties {missing}: {path.name}'
        )
    if len(binary) != expected:
        raise ValueError(
            f'Truncated or non-binary PLY body: {path.name} '
            f'(read {len(binary)} of {expected} bytes)'
        )
    raw = np.frombuffer(binary, dtype=dtype)
    means = np.ascontiguousarray(
        np.column_stack([raw[key] for key in _XYZ_KEYS]).astype(
            np.float32)
    )
    colors = _extract_colors(raw, n_verts)
    logger.debug('Loaded point cloud %s: %d points', path.name, n_verts)
    data = {'means_np': means, 'colors_np': colors}
    if use_cache:
        save_cache_async(path, data, _KIND_POINTCLOUD)
    return data
