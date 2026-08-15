import logging

import numpy as np

from process.overlay_coord import (
    display_axis_to_object_axis, display_rot_to_object_rot,
    display_to_object_center, euler_xyz_to_matrix, matrix_to_euler_xyz,
    object_center_to_display, object_rot_to_display_rot, reorthogonalize)

logger = logging.getLogger(__name__)

_MIN_BASE = 0.000000001

def to_display_center(center: np.ndarray) -> np.ndarray:
    return object_center_to_display(center)

def from_display_center(vec: np.ndarray) -> np.ndarray:
    return display_to_object_center(vec).astype(np.float32)

def display_center_axis(center: np.ndarray, i: int) -> float:
    return float(to_display_center(center)[i])

def set_display_center_axis(
    center: np.ndarray, i: int, value: float,
) -> np.ndarray:
    d = to_display_center(center)
    d[i] = float(value)
    return from_display_center(d)

def to_display_scale(size: np.ndarray, base: np.ndarray) -> np.ndarray:
    out = np.ones(3, dtype=np.float64)
    for i in range(3):
        j = display_axis_to_object_axis(i)
        b = float(base[j])
        out[i] = float(size[j]) / b if b > _MIN_BASE else 1.0
    return out

def from_display_scale(
    values: np.ndarray, base: np.ndarray,
) -> np.ndarray:
    out = np.zeros(3, dtype=np.float32)
    for i in range(3):
        j = display_axis_to_object_axis(i)
        out[j] = max(0.0, float(values[i])) * float(base[j])
    return out

def display_scale_axis(size: np.ndarray, base: np.ndarray, i: int) -> float:
    return float(to_display_scale(size, base)[i])

def set_display_scale_axis(
    size: np.ndarray, base: np.ndarray, i: int, value: float,
) -> np.ndarray:
    out = np.asarray(size, dtype=np.float32).copy()
    j = display_axis_to_object_axis(i)
    out[j] = max(0.0, float(value)) * float(base[j])
    return out

def to_display_euler(
    rot: np.ndarray, base: np.ndarray | None = None,
) -> np.ndarray:
    r = np.asarray(rot, dtype=np.float32)
    if base is not None:
        r = r @ np.asarray(base, dtype=np.float32).T
    return matrix_to_euler_xyz(object_rot_to_display_rot(r))

def from_display_euler(
    deg: np.ndarray, base: np.ndarray | None = None,
) -> np.ndarray:
    disp = euler_xyz_to_matrix(np.asarray(deg, dtype=np.float32))
    raw = display_rot_to_object_rot(disp)
    if base is not None:
        raw = raw @ np.asarray(base, dtype=np.float32)
    return reorthogonalize(raw)

def display_euler_axis(
    rot: np.ndarray, i: int, base: np.ndarray | None = None,
) -> float:
    return float(to_display_euler(rot, base)[i])

def set_display_euler_axis(
    rot: np.ndarray, i: int, value: float,
    base: np.ndarray | None = None,
) -> np.ndarray:
    e = to_display_euler(rot, base)
    e[i] = float(value)
    return from_display_euler(e, base)
