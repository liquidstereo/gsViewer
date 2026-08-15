import numpy as np
import torch

def to_local_norm(
    means: torch.Tensor,
    center: np.ndarray,
    rotation: np.ndarray,
    size: np.ndarray,
) -> torch.Tensor:
    c = torch.as_tensor(center, device=means.device, dtype=means.dtype)
    r = torch.as_tensor(rotation, device=means.device, dtype=means.dtype)
    half = torch.as_tensor(
        size, device=means.device, dtype=means.dtype,
    ) * 0.5
    half = torch.clamp(half, min=0.000001)
    local = (means - c) @ r
    return local / half

def ramp_val(
    local_norm: torch.Tensor, shape: str, axis: int,
) -> torch.Tensor:
    if shape == 'linear':
        return torch.clamp((local_norm[:, axis] + 1.0) * 0.5, 0.0, 1.0)
    if shape == 'box':
        return torch.clamp(local_norm.abs().amax(dim=-1), 0.0, 1.0)
    return torch.clamp(local_norm.norm(dim=-1), 0.0, 1.0)

def region_inside(
    local_norm: torch.Tensor, shape: str, edge: float,
) -> torch.Tensor:
    if shape == 'spherical':
        metric = local_norm.norm(dim=-1)
    else:
        metric = local_norm.abs().amax(dim=-1)
    t = ((metric - 1.0) / max(edge, 0.000001)).clamp(0.0, 1.0)
    return 1.0 - (t * t * (3.0 - 2.0 * t))
