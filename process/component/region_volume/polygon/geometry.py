import numpy as np
import torch

_EPS: float = 0.000000001

def point_in_polygon_t(
    pu: torch.Tensor, pv: torch.Tensor, verts: torch.Tensor,
) -> torch.Tensor:
    xi = verts[:, 0][None, :]
    yi = verts[:, 1][None, :]
    xj = torch.roll(verts[:, 0], -1)[None, :]
    yj = torch.roll(verts[:, 1], -1)[None, :]
    px = pu[:, None]
    py = pv[:, None]
    cond_y = (yi > py) != (yj > py)
    x_int = (xj - xi) * (py - yi) / (yj - yi + _EPS) + xi
    cross = cond_y & (px < x_int)
    return (cross.sum(dim=1) % 2) == 1

def edge_distance_t(
    pu: torch.Tensor, pv: torch.Tensor, verts: torch.Tensor,
) -> torch.Tensor:
    p = torch.stack([pu, pv], dim=1)
    m = verts.shape[0]
    best: torch.Tensor | None = None
    for i in range(m):
        a = verts[i]
        b = verts[(i + 1) % m]
        ab = b - a
        denom = float(torch.dot(ab, ab)) + _EPS
        ap = p - a
        t = ((ap @ ab) / denom).clamp(0.0, 1.0)
        proj = a[None, :] + t[:, None] * ab[None, :]
        d = torch.linalg.vector_norm(p - proj, dim=1)
        best = d if best is None else torch.minimum(best, d)
    if best is None:
        return torch.zeros_like(pu)
    return best

def polygon_extents(verts2d: np.ndarray) -> tuple[float, float]:
    if len(verts2d) == 0:
        return 1.0, 1.0
    su = float(2.0 * np.max(np.abs(verts2d[:, 0])))
    sv = float(2.0 * np.max(np.abs(verts2d[:, 1])))
    return max(su, 0.001), max(sv, 0.001)
