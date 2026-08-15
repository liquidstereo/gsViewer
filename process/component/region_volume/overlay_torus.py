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
from process.component.region_volume.region_torus import torus_radii

logger = logging.getLogger(__name__)

_RING_SEGMENTS: int = 64
_TUBE_SEGMENTS: int = 24
_TUBE_COUNT: int = 4

def _hring_pairs(
    n: int, radius: float, z_local: float,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    thetas = np.linspace(0.0, 2.0 * np.pi, n + 1, dtype=np.float32)
    pts_local = np.zeros((n + 1, 3), dtype=np.float32)
    pts_local[:, 0] = radius * np.cos(thetas)
    pts_local[:, 1] = radius * np.sin(thetas)
    pts_local[:, 2] = z_local
    world = pts_local @ rotation.T + center
    return [(world[i], world[i + 1]) for i in range(n)]

def _tube_circle_pairs(
    n: int, R: float, r: float, alpha: float,
    rotation: np.ndarray, center: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    ca, sa = float(np.cos(alpha)), float(np.sin(alpha))
    radial = np.array([ca, sa, 0.0], dtype=np.float32)
    z_hat = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    ring_c = R * radial
    beta = np.linspace(0.0, 2.0 * np.pi, n + 1, dtype=np.float32)
    pts_local = (
        ring_c
        + r * np.cos(beta)[:, None] * radial
        + r * np.sin(beta)[:, None] * z_hat
    ).astype(np.float32)
    world = pts_local @ rotation.T + center
    return [(world[i], world[i + 1]) for i in range(n)]

def compute_torus_segments(
    win: Any, region: Any, samples: int = _RING_SEGMENTS,
) -> list:
    mats = _get_view_mats(win)
    if mats is None:
        return []
    vm, K_np = mats
    half = np.maximum(np.asarray(region.size, dtype=np.float32) * 0.5, 0.001)
    rotation = np.asarray(region.rotation, dtype=np.float32)
    center = np.asarray(region.center, dtype=np.float32)
    R, r = torus_radii(half)
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    pairs.extend(_hring_pairs(samples, R + r, 0.0, rotation, center))
    pairs.extend(_hring_pairs(samples, max(R - r, 0.001), 0.0,
                              rotation, center))
    pairs.extend(_hring_pairs(samples, R, +r, rotation, center))
    pairs.extend(_hring_pairs(samples, R, -r, rotation, center))
    for i in range(_TUBE_COUNT):
        alpha = 2.0 * np.pi * i / _TUBE_COUNT
        pairs.extend(_tube_circle_pairs(
            _TUBE_SEGMENTS, R, r, alpha, rotation, center,
        ))
    return _project_segments(pairs, vm, K_np, _is_ortho(win))

def paint_torus_region(
    painter: QPainter, win: Any, region: Any,
    w: int, h: int, depth: np.ndarray | None,
    palette: RegionPalette | None = None,
    selected: bool = False,
) -> None:
    paint_shape_region(
        painter, win, region, w, h, depth,
        compute_torus_segments(win, region),
        palette, selected,
    )

def make_torus_painter(
    plugin: Any, window: Any,
    palette: RegionPalette | None = None,
) -> Callable[[QPainter, int, int, np.ndarray | None], None]:
    return make_shape_painter(
        plugin, window, paint_torus_region, palette,
    )
