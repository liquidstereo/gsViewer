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

def _cap_ring_pairs(
    n: int, half: np.ndarray, z_local: float,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    thetas = np.linspace(0.0, 2.0 * np.pi, n + 1, dtype=np.float32)
    pts_local = np.zeros((n + 1, 3), dtype=np.float32)
    pts_local[:, 0] = float(half[0]) * np.cos(thetas)
    pts_local[:, 1] = float(half[1]) * np.sin(thetas)
    pts_local[:, 2] = float(z_local)
    pts_world = pts_local @ rotation.T + center
    return [(pts_world[i], pts_world[i + 1]) for i in range(n)]

def _side_pairs(
    half: np.ndarray, rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    hx, hy, hz = float(half[0]), float(half[1]), float(half[2])
    locals_ = np.array([
        [+hx, 0.0, -hz], [+hx, 0.0, +hz],
        [-hx, 0.0, -hz], [-hx, 0.0, +hz],
        [0.0, +hy, -hz], [0.0, +hy, +hz],
        [0.0, -hy, -hz], [0.0, -hy, +hz],
    ], dtype=np.float32)
    world = locals_ @ rotation.T + center
    return [
        (world[0], world[1]),
        (world[2], world[3]),
        (world[4], world[5]),
        (world[6], world[7]),
    ]

def compute_cylinder_segments(
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
    pairs.extend(_cap_ring_pairs(
        samples, half, +float(half[2]), rotation, center,
    ))
    pairs.extend(_cap_ring_pairs(
        samples, half, -float(half[2]), rotation, center,
    ))
    pairs.extend(_side_pairs(half, rotation, center))
    return _project_segments(pairs, vm, K_np, _is_ortho(win))

def paint_cylinder_region(
    painter: QPainter, win: Any, region: Any,
    w: int, h: int, depth: np.ndarray | None,
    palette: RegionPalette | None = None,
    selected: bool = False,
) -> None:
    paint_shape_region(
        painter, win, region, w, h, depth,
        compute_cylinder_segments(win, region),
        palette, selected,
    )

def make_cylinder_painter(
    plugin: Any, window: Any,
    palette: RegionPalette | None = None,
) -> Callable[[QPainter, int, int, np.ndarray | None], None]:
    return make_shape_painter(
        plugin, window, paint_cylinder_region, palette,
    )
