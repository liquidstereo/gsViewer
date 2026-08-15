import torch

from process.component.ramp import apply_ramp_mult

__all__ = [
    'apply_displacement', 'apply_opacity_gate', 'apply_ramp_mult',
    'apply_scale_gate', 'apply_size_variability',
]

def apply_displacement(
    means: torch.Tensor,
    offset: torch.Tensor,
    weight: torch.Tensor,
) -> torch.Tensor:
    return means + offset * weight.unsqueeze(-1)

def apply_opacity_gate(
    opacities: torch.Tensor,
    region_mask: torch.Tensor,
    reveal: torch.Tensor,
    min_opacity: float,
) -> torch.Tensor:
    gate = 1.0 - region_mask * (1.0 - min_opacity) * (1.0 - reveal)
    return (opacities * gate).clamp(0.0, 1.0)

def apply_scale_gate(
    scales: torch.Tensor,
    region_mask: torch.Tensor,
    reveal: torch.Tensor,
    min_size: float,
) -> torch.Tensor:
    gate = 1.0 - region_mask * (1.0 - min_size) * (1.0 - reveal)
    return scales * gate.unsqueeze(-1)

def apply_size_variability(
    scales: torch.Tensor,
    region_mask: torch.Tensor,
    dist: torch.Tensor,
    amount: float,
    edge_min: float,
) -> torch.Tensor:
    factor = 1.0 - region_mask * amount * (1.0 - edge_min) * dist
    return scales * factor.unsqueeze(-1)
