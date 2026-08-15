import logging

import numpy as np
import torch

from configs.settings_camera import WORLD_ROT
from configs.settings_color import (
    AXIS_X_COLOR, AXIS_Y_COLOR, AXIS_Z_COLOR,
)
from process.camera import viewmat_to_numpy
from process.widget.scale import scaled_axis_origin, scaled_axis_scale

logger = logging.getLogger(__name__)

_WORLD_ROT = np.array(WORLD_ROT, dtype=np.float32)

_AXES_DISPLAY_YUP: tuple = (
    (np.array([1.0, 0.0, 0.0], dtype=np.float32), AXIS_X_COLOR, 'X'),
    (np.array([0.0, -1.0, 0.0], dtype=np.float32), AXIS_Y_COLOR, 'Y'),
    (np.array([0.0, 0.0, -1.0], dtype=np.float32), AXIS_Z_COLOR, 'Z'),
)

_GIZMO_SIGN = np.diag([
    _AXES_DISPLAY_YUP[0][0][0],
    _AXES_DISPLAY_YUP[1][0][1],
    _AXES_DISPLAY_YUP[2][0][2],
]).astype(np.float32)
_M = (_GIZMO_SIGN @ _WORLD_ROT).astype(np.float32)
_AXIS_PERM = tuple(int(np.argmax(np.abs(_M[i]))) for i in range(3))

_BASE_OBJECT_AXES = (
    np.stack([a[0] for a in _AXES_DISPLAY_YUP]) @ _WORLD_ROT
).astype(np.float32)

def object_gizmo_axes(rotation: np.ndarray) -> np.ndarray:
    r = np.asarray(rotation, dtype=np.float32)
    return (_BASE_OBJECT_AXES @ r.T).astype(np.float32)

def region_gizmo_axes(rotation: np.ndarray) -> np.ndarray:
    return np.asarray(rotation, dtype=np.float32).T.astype(np.float32)

def object_center_to_display(v: np.ndarray) -> np.ndarray:
    return _M @ np.asarray(v, dtype=np.float32)

def display_to_object_center(v: np.ndarray) -> np.ndarray:
    return _M.T @ np.asarray(v, dtype=np.float32)

def object_rot_to_display_rot(r: np.ndarray) -> np.ndarray:
    return (_M @ np.asarray(r, dtype=np.float32) @ _M.T).astype(np.float32)

def display_rot_to_object_rot(r: np.ndarray) -> np.ndarray:
    return (_M.T @ np.asarray(r, dtype=np.float32) @ _M).astype(np.float32)

def euler_xyz_to_matrix(deg: np.ndarray) -> np.ndarray:
    a, b, c = (float(np.radians(v)) for v in deg)
    ca, sa = np.cos(a), np.sin(a)
    cb, sb = np.cos(b), np.sin(b)
    cc, sc = np.cos(c), np.sin(c)
    rx = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]], dtype=np.float32)
    ry = np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]], dtype=np.float32)
    rz = np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]], dtype=np.float32)
    return (rz @ ry @ rx).astype(np.float32)

def matrix_to_euler_xyz(r: np.ndarray) -> np.ndarray:
    m = np.asarray(r, dtype=np.float32)
    sy = float(np.clip(-m[2, 0], -1.0, 1.0))
    ry = np.arcsin(sy)
    if abs(m[2, 0]) < 0.999999:
        rx = np.arctan2(m[2, 1], m[2, 2])
        rz = np.arctan2(m[1, 0], m[0, 0])
    else:
        rx = np.arctan2(-m[1, 2], m[1, 1])
        rz = 0.0
    return np.degrees(
        np.array([rx, ry, rz], dtype=np.float32)).astype(np.float32)

def reorthogonalize(r: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(np.asarray(r, dtype=np.float32))
    return (u @ vt).astype(np.float32)

def display_axis_to_object_axis(i: int) -> int:
    return _AXIS_PERM[i]

def _pure_cam_rotation(viewmat: torch.Tensor) -> np.ndarray:
    R_full = viewmat[0, :3, :3].cpu().numpy()
    return R_full @ _WORLD_ROT.T

def display_eye_yup_from_viewmat(
    viewmat: torch.Tensor,
) -> np.ndarray:
    mat = viewmat_to_numpy(viewmat)

    eye_ply = -(mat[:3, :3].T @ mat[:3, 3])

    eye_disp = _WORLD_ROT @ eye_ply

    return np.array(
        [eye_disp[0], -eye_disp[1], eye_disp[2]], dtype=np.float32,
    )

def compute_gizmo_axes(
    viewmat: torch.Tensor, h: int, w: int,
) -> list[tuple[int, int, int, int, str, str]]:
    R = _pure_cam_rotation(viewmat)
    cx, cy = scaled_axis_origin(w, h)
    sc = scaled_axis_scale(w)
    result: list = []
    for axis, color, label in _AXES_DISPLAY_YUP:
        d = R @ axis
        ex = cx + int(d[0] * sc)
        ey = cy + int(d[1] * sc)
        result.append((cx, cy, ex, ey, color, label))
    return result
