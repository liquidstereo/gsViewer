import numpy as np
import torch

from process.component.region_volume.picking_shapes import ray_cylinder
from process.component.region_volume.region_base import RegionTransformBase

_MIN_SIZE: float = 0.001
_EPS: float = 0.000001

def _smoothstep(t: torch.Tensor) -> torch.Tensor:
    return t * t * (3.0 - 2.0 * t)

class RegionCylinder(RegionTransformBase):

    _shape_name: str = 'cylinder'
    _log_label: str = 'Cylinder'

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        half = np.maximum(self.size * 0.5, _MIN_SIZE)
        c = torch.from_numpy(self.center).to(means.device, means.dtype)
        R = torch.from_numpy(self.rotation).to(means.device, means.dtype)
        h = torch.from_numpy(half).to(means.device, means.dtype)
        local = (means - c) @ R
        nx = local[:, 0] / h[0]
        ny = local[:, 1] / h[1]
        nz_abs = torch.abs(local[:, 2]) / h[2]
        radial = torch.sqrt(nx * nx + ny * ny)
        soft = float(max(self.softness, _EPS))
        t_r = (((1.0 + soft) - radial) / (2.0 * soft)).clamp(0.0, 1.0)
        t_z = (((1.0 + soft) - nz_abs) / (2.0 * soft)).clamp(0.0, 1.0)
        return _smoothstep(t_r) * _smoothstep(t_z)

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        return ray_cylinder(
            origin, direction, self.center, self.size * 0.5, self.rotation,
        )
