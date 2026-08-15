import torch

def apply_crop_mask(
    opacities: torch.Tensor,
    mask: torch.Tensor,
    invert: bool,
) -> torch.Tensor:
    gate = (1.0 - mask) if invert else mask
    return (opacities * gate).clamp(0.0, 1.0)
