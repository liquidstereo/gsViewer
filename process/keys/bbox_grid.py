import math

import numpy as np
import torch

from configs.settings_window import GRID_DIVISIONS
from process.camera import viewmat_K_to_numpy

def _get_view_mats(
    viewmat, K,
) -> tuple[np.ndarray, np.ndarray]:
    return viewmat_K_to_numpy(viewmat, K)

def _means_bounds(splat: dict) -> tuple[np.ndarray, np.ndarray]:

    means = splat['means']
    both = torch.stack(
        [means.min(0).values, means.max(0).values]
    ).cpu().numpy()
    return both[0], both[1]

def _project_point(
    p: np.ndarray, vm: np.ndarray, K_np: np.ndarray,
    ortho: bool = False,
) -> tuple[int, int] | None:
    c = (vm @ np.append(p, 1.0))[:3]
    if c[2] <= 0:
        return None
    if ortho:
        return (
            int(K_np[0, 0] * c[0] + K_np[0, 2]),
            int(K_np[1, 1] * c[1] + K_np[1, 2]),
        )
    return (
        int(K_np[0, 0] * c[0] / c[2] + K_np[0, 2]),
        int(K_np[1, 1] * c[1] / c[2] + K_np[1, 2]),
    )

def _project_segments(
    segs: list[tuple[np.ndarray, np.ndarray]],
    vm: np.ndarray,
    K_np: np.ndarray,
    ortho: bool = False,
) -> list[tuple[int, int, float, int, int, float]]:
    lines = []
    for p1, p2 in segs:
        c1 = (vm @ np.append(p1, 1.0))[:3]
        c2 = (vm @ np.append(p2, 1.0))[:3]
        if c1[2] <= 0 or c2[2] <= 0:
            continue
        if ortho:
            x1 = int(K_np[0, 0] * c1[0] + K_np[0, 2])
            y1 = int(K_np[1, 1] * c1[1] + K_np[1, 2])
            x2 = int(K_np[0, 0] * c2[0] + K_np[0, 2])
            y2 = int(K_np[1, 1] * c2[1] + K_np[1, 2])
        else:
            x1 = int(K_np[0, 0] * c1[0] / c1[2] + K_np[0, 2])
            y1 = int(K_np[1, 1] * c1[1] / c1[2] + K_np[1, 2])
            x2 = int(K_np[0, 0] * c2[0] / c2[2] + K_np[0, 2])
            y2 = int(K_np[1, 1] * c2[1] / c2[2] + K_np[1, 2])
        lines.append((x1, y1, float(c1[2]), x2, y2, float(c2[2])))
    return lines

def _project_pane_corners(
    corners: list[np.ndarray],
    vm: np.ndarray,
    K_np: np.ndarray,
    ortho: bool = False,
) -> list[tuple[int, int]] | None:
    pts = [_project_point(p, vm, K_np, ortho) for p in corners]
    if any(p is None for p in pts):
        return None
    return pts

def _nice_step(span: float) -> float:
    if span <= 0:
        return 1.0
    raw = span / GRID_DIVISIONS
    mag = 10 ** math.floor(math.log10(raw))
    n = raw / mag
    if n <= 1:
        return mag
    if n <= 2:
        return 2 * mag
    if n <= 5:
        return 5 * mag
    return 10 * mag

def _build_labels(
    mn: np.ndarray,
    mx: np.ndarray,
    xf: float,
    yf: float,
    zf: float,
    vm: np.ndarray,
    K_np: np.ndarray,
    ortho: bool = False,
) -> tuple[list, list]:
    ticks = []
    axis_cfg = [
        (0, mn[0], mx[0], yf, zf),
        (1, mn[1], mx[1], xf, zf),
        (2, mn[2], mx[2], xf, yf),
    ]
    for axis, v_min, v_max, fa, fb in axis_cfg:
        step = _nice_step(v_max - v_min)
        start = math.ceil(v_min / step) * step
        count = max(1, round((v_max - start) / step) + 1)
        for k in range(count):
            v = start + k * step
            if v > v_max + 0.000000001:
                break
            if axis == 0:
                p = np.array([v, fa, fb])
            elif axis == 1:
                p = np.array([fa, v, fb])
            else:
                p = np.array([fa, fb, v])
            pt = _project_point(p, vm, K_np, ortho)
            if pt:
                ticks.append((pt[0], pt[1], f'{v:.3g}'))

    center = (mn + mx) / 2
    axis_labels = []
    for label, p3d in [
        ('X', np.array([center[0], yf, zf])),
        ('Y', np.array([xf, center[1], zf])),
        ('Z', np.array([xf, yf, center[2]])),
    ]:
        pt = _project_point(p3d, vm, K_np, ortho)
        if pt:
            axis_labels.append((pt[0] + 8, pt[1] - 8, label))

    return ticks, axis_labels

def compute_bbox_lines(
    splat: dict, viewmat: torch.Tensor, K: torch.Tensor,
    ortho: bool = False,
    bounds: tuple[np.ndarray, np.ndarray] | None = None,
) -> list[tuple[int, int, int, int]]:
    mn, mx = bounds if bounds is not None else _means_bounds(splat)
    c = np.array([
        [mn[0], mn[1], mn[2]], [mx[0], mn[1], mn[2]],
        [mx[0], mx[1], mn[2]], [mn[0], mx[1], mn[2]],
        [mn[0], mn[1], mx[2]], [mx[0], mn[1], mx[2]],
        [mx[0], mx[1], mx[2]], [mn[0], mx[1], mx[2]],
    ])
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    vm, K_np = _get_view_mats(viewmat, K)
    return _project_segments(
        [(c[i], c[j]) for i, j in edges], vm, K_np, ortho,
    )

def compute_grid(
    splat: dict, viewmat: torch.Tensor, K: torch.Tensor,
    ortho: bool = False,
    bounds: tuple[np.ndarray, np.ndarray] | None = None,
) -> dict:
    mn, mx = bounds if bounds is not None else _means_bounds(splat)
    vm, K_np = _get_view_mats(viewmat, K)
    cam = -(vm[:3, :3].T @ vm[:3, 3])
    center = (mn + mx) / 2

    xf = mn[0] if cam[0] > center[0] else mx[0]
    yf = mn[1] if cam[1] > center[1] else mx[1]
    zf = mn[2] if cam[2] > center[2] else mx[2]

    n = GRID_DIVISIONS + 1
    xs = np.linspace(mn[0], mx[0], n)
    ys = np.linspace(mn[1], mx[1], n)
    zs = np.linspace(mn[2], mx[2], n)

    floor = []
    for x in xs:
        floor.append((np.array([x, yf, mn[2]]),
                      np.array([x, yf, mx[2]])))
    for z in zs:
        floor.append((np.array([mn[0], yf, z]),
                      np.array([mx[0], yf, z])))

    wall_x = []
    for y in ys:
        wall_x.append((np.array([xf, y, mn[2]]),
                       np.array([xf, y, mx[2]])))
    for z in zs:
        wall_x.append((np.array([xf, mn[1], z]),
                       np.array([xf, mx[1], z])))

    wall_z = []
    for x in xs:
        wall_z.append((np.array([x, mn[1], zf]),
                       np.array([x, mx[1], zf])))
    for y in ys:
        wall_z.append((np.array([mn[0], y, zf]),
                       np.array([mx[0], y, zf])))

    ticks, axis_labels = _build_labels(
        mn, mx, xf, yf, zf, vm, K_np, ortho,
    )

    floor_corners = [
        np.array([mn[0], yf, mn[2]]), np.array([mx[0], yf, mn[2]]),
        np.array([mx[0], yf, mx[2]]), np.array([mn[0], yf, mx[2]]),
    ]
    wall_x_corners = [
        np.array([xf, mn[1], mn[2]]), np.array([xf, mx[1], mn[2]]),
        np.array([xf, mx[1], mx[2]]), np.array([xf, mn[1], mx[2]]),
    ]
    wall_z_corners = [
        np.array([mn[0], mn[1], zf]), np.array([mx[0], mn[1], zf]),
        np.array([mx[0], mx[1], zf]), np.array([mn[0], mx[1], zf]),
    ]

    return {
        'pane_floor':  _project_pane_corners(floor_corners,  vm, K_np, ortho),
        'pane_wall_l': _project_pane_corners(wall_x_corners, vm, K_np, ortho),
        'pane_wall_b': _project_pane_corners(wall_z_corners, vm, K_np, ortho),
        'floor':       _project_segments(floor,  vm, K_np, ortho),
        'wall_l':      _project_segments(wall_x, vm, K_np, ortho),
        'wall_b':      _project_segments(wall_z, vm, K_np, ortho),
        'ticks':       ticks,
        'axis_labels': axis_labels,
    }

def compute_bbox_grid(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    ortho: bool = False,
    want_bbox: bool = True,
    want_grid: bool = True,
) -> tuple[list | None, dict | None]:
    if not want_bbox and not want_grid:
        return None, None
    bounds = _means_bounds(splat)
    bbox = (
        compute_bbox_lines(splat, viewmat, K, ortho, bounds)
        if want_bbox else None
    )
    grid = (
        compute_grid(splat, viewmat, K, ortho, bounds)
        if want_grid else None
    )
    return bbox, grid
