import math

import torch

def _feature_offset(
    cell: torch.Tensor, t: float, speed: float, ph: torch.Tensor,
) -> torch.Tensor:
    seed = torch.tensor(
        [12.9898, 78.233, 37.719],
        device=cell.device, dtype=cell.dtype,
    )
    h = torch.sin(cell @ seed) * 43758.5453
    h = h - torch.floor(h)
    wt = t * speed
    phase = torch.tensor(
        [wt + ph[0].item(),
         1.7 * wt + ph[1].item(),
         0.5 * wt + ph[2].item()],
        device=cell.device, dtype=cell.dtype,
    )
    return 0.5 + 0.4 * torch.sin(
        h.unsqueeze(1) * (2.0 * math.pi) + phase
    )

def apply(
    means: torch.Tensor, t: float, level: float, gain: float,
    freq: float, speed: float, octaves: int, phases: torch.Tensor,
) -> torch.Tensor:
    _ = octaves
    p = means * freq
    cell = torch.floor(p)
    frac = p - cell
    feat = _feature_offset(cell, t, speed, phases[0])

    diff = frac - feat
    return means + diff * (gain * level)
