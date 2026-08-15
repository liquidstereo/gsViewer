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
from process.component.region_volume.polygon.settings import POLYGON_MIN_VERTS

logger = logging.getLogger(__name__)

def _face_world(
    verts2d: np.ndarray, center: np.ndarray, u: np.ndarray,
    v: np.ndarray, n: np.ndarray, n_off: float,
) -> np.ndarray:
    base = center + n * n_off
    return base + verts2d[:, 0:1] * u + verts2d[:, 1:2] * v

def _loop_pairs(
    pts: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    n = len(pts)
    return [(pts[i], pts[(i + 1) % n]) for i in range(n)]

def compute_polygon_segments(win: Any, region: Any) -> list:
    if (not getattr(region, 'committed', False)
            or len(region.verts2d) < POLYGON_MIN_VERTS):
        return []
    mats = _get_view_mats(win)
    if mats is None:
        return []
    vm, K_np = mats
    rot = np.asarray(region.rotation, dtype=np.float32)
    center = np.asarray(region.center, dtype=np.float32)
    verts = np.asarray(region.verts2d, dtype=np.float32)
    u, v, n = rot[:, 0], rot[:, 1], rot[:, 2]
    half_d = float(region.size[2]) * 0.5
    front = _face_world(verts, center, u, v, n, -half_d)
    back = _face_world(verts, center, u, v, n, +half_d)
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    pairs.extend(_loop_pairs(front))
    pairs.extend(_loop_pairs(back))
    pairs.extend((front[i], back[i]) for i in range(len(front)))
    return _project_segments(pairs, vm, K_np, _is_ortho(win))

def paint_polygon_region(
    painter: QPainter, win: Any, region: Any,
    w: int, h: int, depth: np.ndarray | None,
    palette: RegionPalette | None = None,
    selected: bool = False,
) -> None:
    paint_shape_region(
        painter, win, region, w, h, depth,
        compute_polygon_segments(win, region),
        palette, selected,
    )

def make_polygon_painter(
    plugin: Any, window: Any,
    palette: RegionPalette | None = None,
) -> Callable[[QPainter, int, int, np.ndarray | None], None]:
    return make_shape_painter(
        plugin, window, paint_polygon_region, palette,
    )
