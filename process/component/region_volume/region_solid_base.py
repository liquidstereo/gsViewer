import numpy as np
import torch

from process.component.region_volume.region_base import RegionTransformBase

_MIN_SIZE: float = 0.001
_EPS: float = 0.000001

def smoothstep(t: torch.Tensor) -> torch.Tensor:
    return t * t * (3.0 - 2.0 * t)

def fade_norm(value: torch.Tensor, soft: float) -> torch.Tensor:
    s = float(max(soft, _EPS))
    t = (((1.0 + s) - value) / (2.0 * s)).clamp(0.0, 1.0)
    return smoothstep(t)

class RegionSolid(RegionTransformBase):

    _shape_name: str = 'solid'
    _log_label: str = 'Region'

    def _locals(self, means: torch.Tensor) -> tuple[torch.Tensor, ...]:
        half = np.maximum(self.size * 0.5, _MIN_SIZE)
        c = torch.from_numpy(self.center).to(means.device, means.dtype)
        R = torch.from_numpy(self.rotation).to(means.device, means.dtype)
        h = torch.from_numpy(half).to(means.device, means.dtype)
        return (means - c) @ R, h
