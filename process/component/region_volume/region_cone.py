import logging

import numpy as np
import torch

from process.component.region_volume.picking_shapes import ray_cone
from process.component.region_volume.region_solid_base import (
    RegionSolid, fade_norm, smoothstep,
)

logger = logging.getLogger(__name__)

_EPS: float = 0.000001

class RegionCone(RegionSolid):

    _shape_name: str = 'cone'
    _log_label: str = 'Cone'

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        local, h = self._locals(means)
        radial = torch.sqrt(
            (local[:, 0] / h[0]) ** 2 + (local[:, 1] / h[1]) ** 2,
        )
        uz = local[:, 2] / h[2]
        rmax = ((1.0 - uz) * 0.5).clamp(min=0.0)
        soft = float(max(self.softness, _EPS))
        t_r = (((rmax + soft) - radial) / (2.0 * soft)).clamp(0.0, 1.0)
        return smoothstep(t_r) * fade_norm(torch.abs(uz), self.softness)

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        return ray_cone(
            origin, direction, self.center, self.size * 0.5, self.rotation,
        )
