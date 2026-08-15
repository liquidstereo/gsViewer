import logging

import numpy as np
import torch

from process.component.region_volume.picking_shapes import ray_capsule
from process.component.region_volume.region_solid_base import RegionSolid, fade_norm

logger = logging.getLogger(__name__)

class RegionCapsule(RegionSolid):

    _shape_name: str = 'capsule'
    _log_label: str = 'Capsule'

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        local, h = self._locals(means)
        hx, hy, hz = h[0], h[1], h[2]
        rz = torch.minimum(hx, hy)
        cap_l = torch.clamp(hz - rz, min=0.0)
        rho = torch.sqrt(
            (local[:, 0] / hx) ** 2 + (local[:, 1] / hy) ** 2,
        )
        dz = torch.clamp(torch.abs(local[:, 2]) - cap_l, min=0.0) / rz
        d = torch.sqrt(rho * rho + dz * dz)
        return fade_norm(d, self.softness)

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        return ray_capsule(
            origin, direction, self.center, self.size * 0.5, self.rotation,
        )
