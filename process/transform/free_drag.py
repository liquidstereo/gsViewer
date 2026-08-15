import logging

import numpy as np

from configs.settings_transform import (
    TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
    TRANSFORM_TRACKBALL_RAD_PER_PX,
)
from process.transform.drag import DragState, _snapshot, start_scale
from process.transform.picking import (
    axis_angle_matrix, camera_axes, ray_aabb, ray_plane_intersect,
    screen_ray,
)

logger = logging.getLogger(__name__)

def hit_target_aabb(win, target, mx: int, my: int) -> bool:
    if target is None:
        return False
    ray = screen_ray(win, float(mx), float(my))
    if ray is None:
        return False
    origin, direction = ray
    corners = target.corners()
    lo = corners.min(axis=0)
    hi = corners.max(axis=0)
    return ray_aabb(origin, direction, lo, hi) is not None

def start_free_translate(
    win, target, mx: int, my: int,
) -> DragState | None:
    axes = camera_axes(win)
    ray = screen_ray(win, float(mx), float(my))
    if axes is None or ray is None:
        return None
    origin, direction = ray
    ds = _snapshot(target)
    p0 = ray_plane_intersect(origin, direction, ds.center0, axes[2])
    if p0 is None:
        return None
    ds.mode = 'free_translate'
    ds.plane_n = axes[2].copy()
    ds.start_pt = p0.astype(np.float32)
    return ds

def start_trackball(win, target, mx: int, my: int) -> DragState | None:
    axes = camera_axes(win)
    if axes is None:
        return None
    right, up, _ = axes
    ds = _snapshot(target)
    ds.mode = 'trackball'
    ds.plane_u = right.astype(np.float32)
    ds.plane_v = up.astype(np.float32)
    ds.start_mx = float(mx)
    ds.start_my = float(my)
    return ds

def begin_free_drag(
    win, target, tool_mode: str, mx: int, my: int,
) -> DragState | None:
    if tool_mode == TOOL_TRANSLATE:
        return start_free_translate(win, target, mx, my)
    if tool_mode == TOOL_SCALE:
        return start_scale(win, target, 'uniform', 0, mx, my)
    if tool_mode == TOOL_ROTATE:
        return start_trackball(win, target, mx, my)
    return None

def apply_free_translate(
    win, target, ds: DragState, mx: int, my: int,
) -> None:
    ray = screen_ray(win, float(mx), float(my))
    if ray is None:
        return
    origin, direction = ray
    p = ray_plane_intersect(origin, direction, ds.center0, ds.plane_n)
    if p is None:
        return
    delta = p - ds.start_pt
    target.center = (ds.center0 + delta).astype(np.float32)

def apply_trackball(win, target, ds: DragState, mx: int, my: int) -> None:
    dx = float(mx) - ds.start_mx
    dy = float(my) - ds.start_my
    k = TRANSFORM_TRACKBALL_RAD_PER_PX
    r_yaw = axis_angle_matrix(ds.plane_v, dx * k)
    r_pitch = axis_angle_matrix(ds.plane_u, dy * k)
    r_drag = (r_pitch @ r_yaw).astype(np.float32)
    target.rotation = (r_drag @ ds.rotation0).astype(np.float32)
