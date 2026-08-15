import numpy as np
import torch

from process.component.region_volume.picking_shapes import ray_obb
from process.component.region_volume.region_base import RegionTransformBase

def _smoothstep_axis(
    coord: torch.Tensor, lo: float, hi: float, soft: float,
) -> torch.Tensor:
    if soft <= 0.0:
        return ((coord >= lo) & (coord <= hi)).to(coord.dtype)
    t_lo = ((coord - (lo - soft)) / (2.0 * soft)).clamp(0.0, 1.0)
    t_hi = (((hi + soft) - coord) / (2.0 * soft)).clamp(0.0, 1.0)
    s_lo = t_lo * t_lo * (3.0 - 2.0 * t_lo)
    s_hi = t_hi * t_hi * (3.0 - 2.0 * t_hi)
    return s_lo * s_hi

class RegionBox(RegionTransformBase):

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        half = self.size * 0.5
        soft = float(np.max(half) * self.softness)
        c = torch.from_numpy(self.center).to(means.device, means.dtype)
        R = torch.from_numpy(self.rotation).to(means.device, means.dtype)
        local = (means - c) @ R
        hx, hy, hz = float(half[0]), float(half[1]), float(half[2])
        mx = _smoothstep_axis(local[:, 0], -hx, hx, soft)
        my = _smoothstep_axis(local[:, 1], -hy, hy, soft)
        mz = _smoothstep_axis(local[:, 2], -hz, hz, soft)
        return mx * my * mz

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        return ray_obb(
            origin, direction, self.center, self.size * 0.5, self.rotation,
        )
