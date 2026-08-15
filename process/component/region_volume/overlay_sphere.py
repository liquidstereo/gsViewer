import logging
from typing import Any, Callable

import numpy as np
from PySide6.QtGui import QPainter

from process.keys.bbox_grid import _project_segments
from process.component.region_volume.overlay_shape import (
    make_shape_painter, paint_shape_region,
)
from process.component.region_volume.overlay import (
    RegionPalette,
    _get_view_mats,
    _is_ortho,
)

logger = logging.getLogger(__name__)

_RING_SEGMENTS: int = 48
_PLANES: tuple[tuple[int, int], ...] = ((0, 1), (1, 2), (0, 2))

def _ring_pairs(
    plane: tuple[int, int], n: int, half: np.ndarray,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    a0, a1 = plane
    thetas = np.linspace(0.0, 2.0 * np.pi, n + 1, dtype=np.float32)
    pts_local = np.zeros((n + 1, 3), dtype=np.float32)
    pts_local[:, a0] = float(half[a0]) * np.cos(thetas)
    pts_local[:, a1] = float(half[a1]) * np.sin(thetas)
    pts_world = pts_local @ rotation.T + center
    return [(pts_world[i], pts_world[i + 1]) for i in range(n)]

def compute_sphere_segments(
    win: Any, region: Any, samples: int = _RING_SEGMENTS,
) -> list:
    mats = _get_view_mats(win)
    if mats is None:
        return []
    vm, K_np = mats
    half = np.asarray(region.size, dtype=np.float32) * 0.5
    rotation = np.asarray(region.rotation, dtype=np.float32)
    center = np.asarray(region.center, dtype=np.float32)
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for plane in _PLANES:
        pairs.extend(
            _ring_pairs(plane, samples, half, rotation, center),
        )
    return _project_segments(pairs, vm, K_np, _is_ortho(win))

def paint_sphere_region(
    painter: QPainter, win: Any, region: Any,
    w: int, h: int, depth: np.ndarray | None,
    palette: RegionPalette | None = None,
    selected: bool = False,
) -> None:
    paint_shape_region(
        painter, win, region, w, h, depth,
        compute_sphere_segments(win, region),
        palette, selected,
    )

def make_sphere_painter(
    plugin: Any, window: Any,
    palette: RegionPalette | None = None,
) -> Callable[[QPainter, int, int, np.ndarray | None], None]:
    return make_shape_painter(
        plugin, window, paint_sphere_region, palette,
    )
