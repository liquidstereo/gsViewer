import logging

import numpy as np

from process.overlay_coord import region_gizmo_axes
from process.component.region_volume.picking import (
    axis_angle_matrix, axis_drag_delta, camera_axes, project_point,
    ray_plane_intersect, screen_ray,
)
from process.component.region_volume.settings import (
    REGION_VOLUME_TRACKBALL_RAD_PER_PX,
)

logger = logging.getLogger(__name__)

_MIN_SIZE: float = 0.001

class DragState:
    __slots__ = (
        'mode', 'axis', 'center0', 'size0', 'rotation0', 'anchor',
        's0', 'start_dist', 'plane_u', 'plane_v', 'plane_n', 'angle0',
        'start_mx', 'start_my', 'start_pt',
    )

    def __init__(self) -> None:
        self.mode: str = ''
        self.axis: int = 0
        self.center0: np.ndarray = np.zeros(3, dtype=np.float32)
        self.size0: np.ndarray = np.zeros(3, dtype=np.float32)
        self.rotation0: np.ndarray = np.eye(3, dtype=np.float32)
        self.anchor: np.ndarray = np.zeros(3, dtype=np.float32)
        self.s0: float = 0.0
        self.start_dist: float = 1.0
        self.plane_u: np.ndarray = np.zeros(3, dtype=np.float32)
        self.plane_v: np.ndarray = np.zeros(3, dtype=np.float32)
        self.plane_n: np.ndarray = np.zeros(3, dtype=np.float32)
        self.angle0: float = 0.0
        self.start_mx: float = 0.0
        self.start_my: float = 0.0
        self.start_pt: np.ndarray = np.zeros(3, dtype=np.float32)

def snapshot(target) -> DragState:
    ds = DragState()
    ds.center0 = target.center.copy()
    ds.size0 = target.size.copy()
    ds.rotation0 = target.rotation.copy()
    ds.anchor = target.center.copy()
    return ds

def start_translate(
    win, target, axis: int, mx: int, my: int,
) -> DragState | None:
    ray = screen_ray(win, float(mx), float(my))
    if ray is None:
        return None
    origin, direction = ray
    axes = region_gizmo_axes(target.rotation)
    s0 = axis_drag_delta(origin, direction, target.center, axes[axis])
    if s0 is None:
        return None
    ds = snapshot(target)
    ds.mode = 'translate'
    ds.axis = axis
    ds.s0 = s0
    return ds

def start_scale(
    win, target, kind: str, axis: int, mx: int, my: int,
) -> DragState | None:
    anchor = target.center.astype(np.float32)
    scr = project_point(win, anchor)
    if scr is None:
        return None
    cx, cy, _ = scr
    d0 = max(1.0, float(((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5))
    ds = snapshot(target)
    ds.mode = kind
    ds.axis = axis
    ds.start_dist = d0
    return ds

def start_rotate(
    win, target, axis: int, mx: int, my: int,
) -> DragState | None:
    ray = screen_ray(win, float(mx), float(my))
    if ray is None:
        return None
    origin, direction = ray
    axes = region_gizmo_axes(target.rotation)
    anchor = target.center.astype(np.float32)
    n = axes[axis].astype(np.float32)
    u = axes[(axis + 1) % 3].astype(np.float32)
    v = axes[(axis + 2) % 3].astype(np.float32)
    p = ray_plane_intersect(origin, direction, anchor, n)
    if p is None:
        return None
    d = p - anchor
    angle0 = float(np.arctan2(float(d @ v), float(d @ u)))
    ds = snapshot(target)
    ds.mode = 'rotate'
    ds.axis = axis
    ds.plane_n = n.copy()
    ds.plane_u = u.copy()
    ds.plane_v = v.copy()
    ds.angle0 = angle0
    return ds

def start_free_translate(
    win, target, mx: int, my: int,
) -> DragState | None:
    axes = camera_axes(win)
    ray = screen_ray(win, float(mx), float(my))
    if axes is None or ray is None:
        return None
    origin, direction = ray
    ds = snapshot(target)
    p0 = ray_plane_intersect(origin, direction, ds.center0, axes[2])
    if p0 is None:
        return None
    ds.mode = 'free_translate'
    ds.plane_n = axes[2].copy()
    ds.start_pt = p0.astype(np.float32)
    return ds

def start_trackball(
    win, target, mx: int, my: int,
) -> DragState | None:
    axes = camera_axes(win)
    if axes is None:
        return None
    right, up, _ = axes
    ds = snapshot(target)
    ds.mode = 'trackball'
    ds.plane_u = right.astype(np.float32)
    ds.plane_v = up.astype(np.float32)
    ds.start_mx = float(mx)
    ds.start_my = float(my)
    return ds

def apply_translate(win, target, ds: DragState, mx: int, my: int) -> None:
    ray = screen_ray(win, float(mx), float(my))
    if ray is None:
        return
    origin, direction = ray
    axes_row = ds.rotation0.T[ds.axis]
    s = axis_drag_delta(origin, direction, ds.anchor, axes_row)
    if s is None:
        return
    delta = s - ds.s0
    new_center = ds.center0 + axes_row.astype(np.float32) * delta
    target.center = new_center.astype(np.float32)

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
    k = REGION_VOLUME_TRACKBALL_RAD_PER_PX
    r_yaw = axis_angle_matrix(ds.plane_v, dx * k)
    r_pitch = axis_angle_matrix(ds.plane_u, dy * k)
    r_drag = (r_pitch @ r_yaw).astype(np.float32)
    target.rotation = (r_drag @ ds.rotation0).astype(np.float32)

def apply_scale(win, target, ds: DragState, mx: int, my: int) -> None:
    scr = project_point(win, ds.center0)
    if scr is None:
        return
    cx, cy, _ = scr
    d1 = max(1.0, float(((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5))
    factor = d1 / ds.start_dist
    new_size = ds.size0.copy()
    if ds.mode == 'uniform':
        new_size = ds.size0 * factor
    else:
        new_size[ds.axis] = ds.size0[ds.axis] * factor
    target.size = np.maximum(new_size, _MIN_SIZE).astype(np.float32)

def apply_rotate(win, target, ds: DragState, mx: int, my: int) -> None:
    ray = screen_ray(win, float(mx), float(my))
    if ray is None:
        return
    origin, direction = ray
    p = ray_plane_intersect(origin, direction, ds.anchor, ds.plane_n)
    if p is None:
        return
    d = p - ds.anchor
    ang = float(np.arctan2(float(d @ ds.plane_v), float(d @ ds.plane_u)))
    delta = ang - ds.angle0
    R = axis_angle_matrix(ds.plane_n, delta)
    new_rot = (R @ ds.rotation0).astype(np.float32)
    target.rotation = new_rot
