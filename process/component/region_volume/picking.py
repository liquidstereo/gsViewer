import logging

import numpy as np

logger = logging.getLogger(__name__)

_EPS: float = 0.000001

def _view_mats(win) -> tuple[np.ndarray, np.ndarray] | None:
    viewmat = getattr(win, '_viewmat', None)
    K = getattr(win, '_K', None)
    if viewmat is None or K is None:
        return None
    return viewmat[0].cpu().numpy(), K[0].cpu().numpy()

def _is_ortho(win) -> bool:
    return getattr(win, '_camera_model', 'pinhole') == 'ortho'

def screen_ray(
    win, px: float, py: float,
) -> tuple[np.ndarray, np.ndarray] | None:
    mats = _view_mats(win)
    if mats is None:
        return None
    vm, K = mats
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    R = vm[:3, :3]
    t = vm[:3, 3]
    R_inv = R.T
    if _is_ortho(win):

        cam_pt = np.array([
            (px - cx) / fx, (py - cy) / fy, 0.0,
        ], dtype=np.float32)
        origin = (R_inv @ (cam_pt - t)).astype(np.float32)
        direction = (R_inv @ np.array(
            [0.0, 0.0, 1.0], dtype=np.float32,
        )).astype(np.float32)
        return origin, direction
    cam_dir = np.array([
        (px - cx) / fx, (py - cy) / fy, 1.0,
    ], dtype=np.float32)
    cam_dir /= np.linalg.norm(cam_dir)
    origin = (-R_inv @ t).astype(np.float32)
    direction = (R_inv @ cam_dir).astype(np.float32)
    return origin, direction

def project_point(win, p: np.ndarray) -> tuple[int, int, float] | None:
    mats = _view_mats(win)
    if mats is None:
        return None
    vm, K = mats
    c = vm @ np.append(p.astype(np.float32), 1.0)
    if c[2] <= 0:
        return None
    if _is_ortho(win):
        sx = int(K[0, 0] * c[0] + K[0, 2])
        sy = int(K[1, 1] * c[1] + K[1, 2])
    else:
        sx = int(K[0, 0] * c[0] / c[2] + K[0, 2])
        sy = int(K[1, 1] * c[1] / c[2] + K[1, 2])
    return sx, sy, float(c[2])

def camera_axes(win) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    mats = _view_mats(win)
    if mats is None:
        return None
    vm, _ = mats
    R = vm[:3, :3].astype(np.float32)
    return R[0].copy(), R[1].copy(), R[2].copy()

def ray_aabb(
    origin: np.ndarray, direction: np.ndarray,
    lo: np.ndarray, hi: np.ndarray,
) -> tuple[float, int, int] | None:
    d = direction.astype(np.float64)
    o = origin.astype(np.float64)
    lo64 = lo.astype(np.float64)
    hi64 = hi.astype(np.float64)
    safe_d = np.where(np.abs(d) < _EPS, np.copysign(_EPS, d), d)
    inv_d = 1.0 / safe_d
    t1 = (lo64 - o) * inv_d
    t2 = (hi64 - o) * inv_d
    tmin_arr = np.minimum(t1, t2)
    tmax_arr = np.maximum(t1, t2)
    tmin = float(tmin_arr.max())
    tmax = float(tmax_arr.min())
    if tmax < 0.0 or tmin > tmax:
        return None
    axis = int(tmin_arr.argmax())
    sign = 1 if d[axis] < 0 else -1
    return tmin, axis, sign

def ray_plane_intersect(
    origin: np.ndarray, direction: np.ndarray,
    anchor: np.ndarray, normal: np.ndarray,
) -> np.ndarray | None:
    d = direction.astype(np.float64)
    n = normal.astype(np.float64)
    denom = float(d @ n)
    if abs(denom) < 0.000001:
        return None
    t = float((anchor.astype(np.float64) - origin.astype(np.float64)) @ n)
    t /= denom
    if t <= 0.0:
        return None
    return (origin + direction * t).astype(np.float32)

def axis_angle_matrix(
    axis_vec: np.ndarray, theta: float,
) -> np.ndarray:
    a = axis_vec.astype(np.float64)
    n = float(np.linalg.norm(a))
    if n < 0.000000001:
        return np.eye(3, dtype=np.float32)
    a /= n
    c, s = float(np.cos(theta)), float(np.sin(theta))
    x, y, z = float(a[0]), float(a[1]), float(a[2])
    one_c = 1.0 - c
    R = np.array([
        [c + x * x * one_c,     x * y * one_c - z * s, x * z * one_c + y * s],
        [y * x * one_c + z * s, c + y * y * one_c,     y * z * one_c - x * s],
        [z * x * one_c - y * s, z * y * one_c + x * s, c + z * z * one_c],
    ], dtype=np.float32)
    return R

def axis_drag_delta(
    origin: np.ndarray, direction: np.ndarray,
    anchor: np.ndarray, axis_vec: np.ndarray,
) -> float | None:
    a = axis_vec.astype(np.float64)
    d = direction.astype(np.float64)
    w = (origin - anchor).astype(np.float64)
    b = float(a @ d)
    denom = 1.0 - b * b
    if denom < 0.0001:
        return None
    e = float(d @ w)
    d_ = float(a @ w)
    return float((d_ - b * e) / denom)
