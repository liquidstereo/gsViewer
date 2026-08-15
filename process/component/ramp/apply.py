import torch

def apply_ramp_mult(
    values: torch.Tensor,
    inside: torch.Tensor,
    mult: torch.Tensor,
) -> torch.Tensor:
    eff = 1.0 - inside * (1.0 - mult)
    if values.dim() > 1:
        return values * eff.unsqueeze(-1)
    return values * eff
