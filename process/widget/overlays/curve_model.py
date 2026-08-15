import numpy as np

EASE_LINEAR = 'linear'
EASE_EASE = 'ease'
EASE_IN = 'ease_in'
EASE_OUT = 'ease_out'
EASE_FLAT = 'flat'

CURVE_EASE_MODES = (EASE_LINEAR, EASE_EASE, EASE_IN, EASE_OUT, EASE_FLAT)
CURVE_EASE_LABELS = {
    EASE_LINEAR: 'Linear',
    EASE_EASE: 'Easy Ease',
    EASE_IN: 'Easy In',
    EASE_OUT: 'Easy Out',
    EASE_FLAT: 'Flat',
}

_FLAT_OUT = {EASE_FLAT, EASE_EASE, EASE_OUT}
_FLAT_IN = {EASE_FLAT, EASE_EASE, EASE_IN}

def default_points(n: int) -> list:
    xs = np.linspace(0.0, 1.0, max(2, int(n)))
    return [(float(x), float(x), EASE_EASE) for x in xs]

def _sanitize(points: list) -> list:
    out = []
    for p in points:
        x = min(1.0, max(0.0, float(p[0])))
        y = min(1.0, max(0.0, float(p[1])))
        valid = len(p) > 2 and p[2] in CURVE_EASE_LABELS
        ease = p[2] if valid else EASE_LINEAR
        out.append((x, y, ease))
    return out

def points_to_lut(points: list, n: int) -> np.ndarray:
    pts = sorted(_sanitize(points), key=lambda p: p[0])
    grid = np.linspace(0.0, 1.0, max(2, int(n)))
    if len(pts) < 2:
        y = pts[0][1] if pts else 0.0
        return np.full(grid.shape, y, dtype=np.float32)
    out = np.interp(grid, [p[0] for p in pts], [p[1] for p in pts])
    for (x0, y0, e0), (x1, y1, e1) in zip(pts, pts[1:]):
        dx = x1 - x0
        if dx <= 0.000000001:
            continue
        chord = (y1 - y0) / dx
        m0 = 0.0 if e0 in _FLAT_OUT else chord
        m1 = 0.0 if e1 in _FLAT_IN else chord
        mask = (grid >= x0) & (grid <= x1)
        s = (grid[mask] - x0) / dx
        s2 = s * s
        s3 = s2 * s
        out[mask] = (
            (2 * s3 - 3 * s2 + 1) * y0 + (s3 - 2 * s2 + s) * m0 * dx
            + (-2 * s3 + 3 * s2) * y1 + (s3 - s2) * m1 * dx
        )
    return np.clip(out, 0.0, 1.0).astype(np.float32)

class CurveState:

    def __init__(self, n_points: int = 3, lut_n: int = 256) -> None:
        self._lut_n = int(lut_n)
        self._n_points = int(n_points)
        self.points: list = default_points(n_points)

    def set_points(self, points: list) -> None:
        self.points = sorted(_sanitize(points), key=lambda p: p[0])

    def lut(self) -> np.ndarray:
        return points_to_lut(self.points, self._lut_n)

    def reset(self) -> None:
        self.points = default_points(self._n_points)
