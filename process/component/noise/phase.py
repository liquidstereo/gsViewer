import math

import torch

TWO_PI = 2.0 * math.pi

def ensure_phases(
    cur: torch.Tensor | None, octaves: int | float, ref: torch.Tensor,
) -> torch.Tensor:
    n = max(1, int(octaves))
    if (cur is None or cur.shape[0] != n or cur.device != ref.device
            or cur.dtype != ref.dtype):
        return torch.rand(
            n, 3, device=ref.device, dtype=ref.dtype,
        ) * TWO_PI
    return cur

def ensure_phase_vec(
    cur: torch.Tensor | None, ref: torch.Tensor,
) -> torch.Tensor:
    if (cur is None or cur.device != ref.device
            or cur.dtype != ref.dtype):
        return torch.rand(
            3, device=ref.device, dtype=ref.dtype,
        ) * TWO_PI
    return cur

def brownian_phase_step(
    phases: torch.Tensor, dt: float, rate: float,
) -> torch.Tensor:
    step = math.sqrt(max(dt, 0.0)) * rate
    delta = torch.randn(
        phases.shape, device=phases.device, dtype=phases.dtype,
    ) * step
    return phases + delta
