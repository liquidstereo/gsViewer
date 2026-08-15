import numpy as np
import torch

from process.component.region_volume.picking_shapes import ray_ellipsoid
from process.component.region_volume.region_base import RegionTransformBase

_MIN_SIZE: float = 0.001
_EPS: float = 0.000001

class RegionSphere(RegionTransformBase):

    _shape_name: str = 'sphere'
    _log_label: str = 'Sphere'

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        half = np.maximum(self.size * 0.5, _MIN_SIZE)
        c = torch.from_numpy(self.center).to(means.device, means.dtype)
        R = torch.from_numpy(self.rotation).to(means.device, means.dtype)
        h = torch.from_numpy(half).to(means.device, means.dtype)
        local = (means - c) @ R
        n = local / h
        r = torch.linalg.vector_norm(n, dim=1)
        soft = float(max(self.softness, _EPS))
        t = ((1.0 + soft) - r) / (2.0 * soft)
        t = t.clamp(0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        return ray_ellipsoid(
            origin, direction, self.center, self.size * 0.5, self.rotation,
        )
