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
_ARC_SEGMENTS: int = 12

def _capsule_dims(half: np.ndarray) -> tuple[float, float, float, float]:
    hx, hy, hz = float(half[0]), float(half[1]), float(half[2])
    rz = min(hx, hy)
    cap_l = max(hz - rz, 0.0)
    return hx, hy, rz, cap_l

def _ring_pairs(
    n: int, half: np.ndarray, z_local: float,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    thetas = np.linspace(0.0, 2.0 * np.pi, n + 1, dtype=np.float32)
    pts_local = np.zeros((n + 1, 3), dtype=np.float32)
    pts_local[:, 0] = float(half[0]) * np.cos(thetas)
    pts_local[:, 1] = float(half[1]) * np.sin(thetas)
    pts_local[:, 2] = float(z_local)
    world = pts_local @ rotation.T + center
    return [(world[i], world[i + 1]) for i in range(n)]

def _side_pairs(
    hx: float, hy: float, cap_l: float,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    locals_ = np.array([
        [+hx, 0.0, -cap_l], [+hx, 0.0, +cap_l],
        [-hx, 0.0, -cap_l], [-hx, 0.0, +cap_l],
        [0.0, +hy, -cap_l], [0.0, +hy, +cap_l],
        [0.0, -hy, -cap_l], [0.0, -hy, +cap_l],
    ], dtype=np.float32)
    world = locals_ @ rotation.T + center
    return [
        (world[0], world[1]), (world[2], world[3]),
        (world[4], world[5]), (world[6], world[7]),
    ]

def _arc_pairs(
    n: int, axis: int, axis_sign: float, axis_h: float,
    rz: float, cap_z: float, z_sign: float,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    phi = np.linspace(0.0, 0.5 * np.pi, n + 1, dtype=np.float32)
    pts_local = np.zeros((n + 1, 3), dtype=np.float32)
    pts_local[:, axis] = axis_sign * axis_h * np.cos(phi)
    pts_local[:, 2] = cap_z + z_sign * rz * np.sin(phi)
    world = pts_local @ rotation.T + center
    return [(world[i], world[i + 1]) for i in range(n)]

def _cap_arcs(
    hx: float, hy: float, rz: float, cap_l: float,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for z_sign, cap_z in ((+1.0, +cap_l), (-1.0, -cap_l)):
        for axis, axis_h in ((0, hx), (1, hy)):
            for axis_sign in (+1.0, -1.0):
                pairs.extend(_arc_pairs(
                    _ARC_SEGMENTS, axis, axis_sign, axis_h, rz,
                    cap_z, z_sign, rotation, center,
                ))
    return pairs

def compute_capsule_segments(
    win: Any, region: Any, samples: int = _RING_SEGMENTS,
) -> list:
    mats = _get_view_mats(win)
    if mats is None:
        return []
    vm, K_np = mats
    half = np.asarray(region.size, dtype=np.float32) * 0.5
    rotation = np.asarray(region.rotation, dtype=np.float32)
    center = np.asarray(region.center, dtype=np.float32)
    hx, hy, rz, cap_l = _capsule_dims(half)
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    pairs.extend(_ring_pairs(samples, half, +cap_l, rotation, center))
    pairs.extend(_ring_pairs(samples, half, -cap_l, rotation, center))
    pairs.extend(_side_pairs(hx, hy, cap_l, rotation, center))
    pairs.extend(_cap_arcs(hx, hy, rz, cap_l, rotation, center))
    return _project_segments(pairs, vm, K_np, _is_ortho(win))

def paint_capsule_region(
    painter: QPainter, win: Any, region: Any,
    w: int, h: int, depth: np.ndarray | None,
    palette: RegionPalette | None = None,
    selected: bool = False,
) -> None:
    paint_shape_region(
        painter, win, region, w, h, depth,
        compute_capsule_segments(win, region),
        palette, selected,
    )

def make_capsule_painter(
    plugin: Any, window: Any,
    palette: RegionPalette | None = None,
) -> Callable[[QPainter, int, int, np.ndarray | None], None]:
    return make_shape_painter(
        plugin, window, paint_capsule_region, palette,
    )
