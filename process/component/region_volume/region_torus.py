import logging

import numpy as np
import torch

from process.component.region_volume.picking_shapes import ray_obb
from process.component.region_volume.region_solid_base import RegionSolid, fade_norm

logger = logging.getLogger(__name__)

_MIN_R: float = 0.001

def torus_radii(half: np.ndarray) -> tuple[float, float]:
    r = float(max(half[2], _MIN_R))
    R = float(max(0.5 * (half[0] + half[1]) - r, _MIN_R))
    return R, r

class RegionTorus(RegionSolid):

    _shape_name: str = 'torus'
    _log_label: str = 'Torus'

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        local, h = self._locals(means)
        half = np.maximum(self.size * 0.5, _MIN_R)
        R, r = torus_radii(half)
        radial = torch.sqrt(local[:, 0] ** 2 + local[:, 1] ** 2)
        q = radial - R
        dist = torch.sqrt(q * q + local[:, 2] ** 2)
        return fade_norm(dist / r, self.softness)

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        return ray_obb(
            origin, direction, self.center, self.size * 0.5, self.rotation,
        )
