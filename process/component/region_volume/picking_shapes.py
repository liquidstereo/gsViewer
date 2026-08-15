import logging

import numpy as np

logger = logging.getLogger(__name__)

_EPS: float = 0.000001
_MIN_HALF: float = 0.000001

def _to_local(
    origin: np.ndarray, direction: np.ndarray,
    center: np.ndarray, rotation: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    R_T = rotation.T.astype(np.float64)
    o = R_T @ (origin.astype(np.float64) - center.astype(np.float64))
    d = R_T @ direction.astype(np.float64)
    return o, d

def ray_obb(
    origin: np.ndarray, direction: np.ndarray,
    center: np.ndarray, half: np.ndarray,
    rotation: np.ndarray,
) -> float | None:
    h = np.maximum(half.astype(np.float64), _MIN_HALF)
    o, d = _to_local(origin, direction, center, rotation)
    safe_d = np.where(np.abs(d) < _EPS, np.copysign(_EPS, d), d)
    inv = 1.0 / safe_d
    t1 = (-h - o) * inv
    t2 = (h - o) * inv
    tmin = float(np.minimum(t1, t2).max())
    tmax = float(np.maximum(t1, t2).min())
    if tmax < 0.0 or tmin > tmax:
        return None
    return max(tmin, 0.0)

def ray_ellipsoid(
    origin: np.ndarray, direction: np.ndarray,
    center: np.ndarray, half: np.ndarray,
    rotation: np.ndarray,
) -> float | None:
    h = np.maximum(half.astype(np.float64), _MIN_HALF)
    o, d = _to_local(origin, direction, center, rotation)
    o2 = o / h
    d2 = d / h
    a = float(d2 @ d2)
    if a < _EPS:
        return None
    b = float(2.0 * (o2 @ d2))
    c = float(o2 @ o2 - 1.0)
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return None
    sd = float(np.sqrt(disc))
    t1 = (-b - sd) / (2.0 * a)
    t2 = (-b + sd) / (2.0 * a)
    if t2 < 0.0:
        return None
    if t1 < 0.0:
        return 0.0
    return float(t1)

def ray_cylinder(
    origin: np.ndarray, direction: np.ndarray,
    center: np.ndarray, half: np.ndarray,
    rotation: np.ndarray,
) -> float | None:
    h = np.maximum(half.astype(np.float64), _MIN_HALF)
    o, d = _to_local(origin, direction, center, rotation)
    hx, hy, hz = float(h[0]), float(h[1]), float(h[2])
    candidates: list[float] = []
    ux, uy = o[0] / hx, o[1] / hy
    vx, vy = d[0] / hx, d[1] / hy
    A = vx * vx + vy * vy
    B = 2.0 * (ux * vx + uy * vy)
    C = ux * ux + uy * uy - 1.0
    if abs(A) > _EPS:
        disc = B * B - 4.0 * A * C
        if disc >= 0.0:
            sd = float(np.sqrt(disc))
            for t in ((-B - sd) / (2.0 * A), (-B + sd) / (2.0 * A)):
                z = o[2] + t * d[2]
                if -hz <= z <= hz:
                    candidates.append(float(t))
    if abs(d[2]) > _EPS:
        for cap_z in (-hz, +hz):
            t = (cap_z - o[2]) / d[2]
            x = o[0] + t * d[0]
            y = o[1] + t * d[1]
            if (x / hx) ** 2 + (y / hy) ** 2 <= 1.0:
                candidates.append(float(t))
    pos = [t for t in candidates if t >= 0.0]
    if pos:
        return float(min(pos))
    inside_xy = (ux * ux + uy * uy) <= 1.0
    inside_z = -hz <= o[2] <= hz
    if inside_xy and inside_z:
        return 0.0
    return None

def _quad_roots(a: float, b: float, c: float) -> list[float]:
    if abs(a) < _EPS:
        if abs(b) < _EPS:
            return []
        return [-c / b]
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return []
    sd = float(np.sqrt(disc))
    return [(-b - sd) / (2.0 * a), (-b + sd) / (2.0 * a)]

def ray_cone(
    origin: np.ndarray, direction: np.ndarray,
    center: np.ndarray, half: np.ndarray,
    rotation: np.ndarray,
) -> float | None:
    h = np.maximum(half.astype(np.float64), _MIN_HALF)
    o, d = _to_local(origin, direction, center, rotation)
    ou = o / h
    du = d / h
    e = (1.0 - ou[2]) * 0.5
    g = -du[2] * 0.5
    a = du[0] * du[0] + du[1] * du[1] - g * g
    b = 2.0 * (ou[0] * du[0] + ou[1] * du[1]) - 2.0 * e * g
    c = ou[0] * ou[0] + ou[1] * ou[1] - e * e
    candidates: list[float] = []
    for t in _quad_roots(a, b, c):
        z = ou[2] + t * du[2]
        if -1.0 <= z <= 1.0:
            candidates.append(float(t))
    if abs(du[2]) > _EPS:
        t = (-1.0 - ou[2]) / du[2]
        x = ou[0] + t * du[0]
        y = ou[1] + t * du[1]
        if x * x + y * y <= 1.0:
            candidates.append(float(t))
    pos = [t for t in candidates if t >= 0.0]
    if pos:
        return float(min(pos))
    radial0 = ou[0] * ou[0] + ou[1] * ou[1]
    rmax = max((1.0 - ou[2]) * 0.5, 0.0)
    if -1.0 <= ou[2] <= 1.0 and radial0 <= rmax * rmax:
        return 0.0
    return None

def ray_capsule(
    origin: np.ndarray, direction: np.ndarray,
    center: np.ndarray, half: np.ndarray,
    rotation: np.ndarray,
) -> float | None:
    h = np.maximum(half.astype(np.float64), _MIN_HALF)
    o, d = _to_local(origin, direction, center, rotation)
    hx, hy = float(h[0]), float(h[1])
    rz = min(hx, hy)
    cap_l = max(float(h[2]) - rz, 0.0)
    candidates: list[float] = []
    ux, uy = o[0] / hx, o[1] / hy
    vx, vy = d[0] / hx, d[1] / hy
    a = vx * vx + vy * vy
    b = 2.0 * (ux * vx + uy * vy)
    c = ux * ux + uy * uy - 1.0
    for t in _quad_roots(a, b, c):
        z = o[2] + t * d[2]
        if -cap_l <= z <= cap_l:
            candidates.append(float(t))
    cap_half = np.array([hx, hy, rz], dtype=np.float64)
    for sign in (-1.0, +1.0):
        cz = sign * cap_l
        oc = np.array([o[0], o[1], o[2] - cz], dtype=np.float64) / cap_half
        dc = d / cap_half
        for t in _quad_roots(
            float(dc @ dc), float(2.0 * (oc @ dc)), float(oc @ oc - 1.0),
        ):
            z = o[2] + t * d[2]
            if (sign > 0.0 and z >= cap_l) or (sign < 0.0 and z <= -cap_l):
                candidates.append(float(t))
    pos = [t for t in candidates if t >= 0.0]
    if pos:
        return float(min(pos))
    if _capsule_inside(o, hx, hy, rz, cap_l):
        return 0.0
    return None

def _capsule_inside(
    o: np.ndarray, hx: float, hy: float, rz: float, cap_l: float,
) -> bool:
    z = float(o[2])
    if -cap_l <= z <= cap_l:
        return (o[0] / hx) ** 2 + (o[1] / hy) ** 2 <= 1.0
    cz = cap_l if z > 0.0 else -cap_l
    return (
        (o[0] / hx) ** 2 + (o[1] / hy) ** 2 + ((z - cz) / rz) ** 2 <= 1.0
    )
