import logging

import numpy as np

from process.component.region_volume.picking import (
    _view_mats, project_point, ray_plane_intersect,
)

logger = logging.getLogger(__name__)

def _segment_distance(
    px: float, py: float,
    x1: float, y1: float, x2: float, y2: float,
) -> float:
    vx, vy = x2 - x1, y2 - y1
    wx, wy = px - x1, py - y1
    seg_len2 = vx * vx + vy * vy
    if seg_len2 < 1.0:
        dx, dy = px - x1, py - y1
        return float((dx * dx + dy * dy) ** 0.5)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / seg_len2))
    cx, cy = x1 + t * vx, y1 + t * vy
    dx, dy = px - cx, py - cy
    return float((dx * dx + dy * dy) ** 0.5)

def region_volume_world_length(
    win, anchor: np.ndarray, screen_len_px: float,
) -> float:
    mats = _view_mats(win)
    if mats is None:
        return 1.0
    vm, K = mats
    fy = float(K[1, 1])
    if fy < 0.000001:
        return 1.0
    if getattr(win, '_camera_model', 'pinhole') == 'ortho':

        return float(screen_len_px) / fy
    c = vm @ np.append(anchor.astype(np.float32), 1.0)
    z = float(c[2])
    if z <= 0.0:
        return 1.0
    return z * float(screen_len_px) / fy

def pick_rotate_axis(
    win, anchor: np.ndarray, axes: np.ndarray, radius: float,
    mx: int, my: int, tol_world: float,
    origin: np.ndarray, direction: np.ndarray,
) -> int | None:
    del win, mx, my
    best_axis: int | None = None
    best_err = float(tol_world)
    for axis in range(3):
        n = axes[axis].astype(np.float32)
        p = ray_plane_intersect(origin, direction, anchor, n)
        if p is None:
            continue
        d = float(np.linalg.norm(p - anchor))
        err = abs(d - float(radius))
        if err <= best_err:
            best_err = err
            best_axis = axis
    return best_axis

def pick_translate_axis(
    win, anchor: np.ndarray, axes: np.ndarray, axis_len: float,
    mx: int, my: int, tol_px: float,
) -> int | None:
    origin_scr = project_point(win, anchor)
    if origin_scr is None:
        return None
    ox, oy, _ = origin_scr
    best_axis: int | None = None
    best_d = float(tol_px)
    a_anchor = anchor.astype(np.float32)
    for axis in range(3):
        tip = a_anchor + axes[axis].astype(np.float32) * axis_len
        tip_scr = project_point(win, tip)
        if tip_scr is None:
            continue
        tx, ty, _ = tip_scr
        d = _segment_distance(mx, my, ox, oy, tx, ty)
        if d <= best_d:
            best_d = d
            best_axis = axis
    return best_axis
