import torch

def _octave(
    x: torch.Tensor, y: torch.Tensor, z: torch.Tensor,
    k: float, wt: float, amp: float, ph: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    cx = (
        torch.cos(2.0 * k * y + 0.5 * wt + ph[0])
        - torch.cos(k * z + 1.3 * wt + ph[0])
    ) * amp
    cy = (
        torch.cos(2.0 * k * z + 1.1 * wt + ph[1])
        - torch.cos(k * x + 0.7 * wt + ph[1])
    ) * amp
    cz = (
        torch.cos(2.0 * k * x + 0.9 * wt + ph[2])
        - torch.cos(k * y + 1.7 * wt + ph[2])
    ) * amp
    return cx, cy, cz

def apply(
    means: torch.Tensor, t: float, level: float, gain: float,
    freq: float, speed: float, octaves: int, phases: torch.Tensor,
) -> torch.Tensor:
    x = means[:, 0]
    y = means[:, 1]
    z = means[:, 2]
    sum_x = torch.zeros_like(x)
    sum_y = torch.zeros_like(y)
    sum_z = torch.zeros_like(z)
    k = freq
    amp = 1.0
    for o in range(max(1, octaves)):
        wt = t * speed * (1.0 + 0.3 * o)
        ph = phases[o]
        cx, cy, cz = _octave(x, y, z, k, wt, amp, ph)
        sum_x = sum_x + cx
        sum_y = sum_y + cy
        sum_z = sum_z + cz
        k *= 2.0
        amp *= 0.5
    offset = torch.stack([sum_x, sum_y, sum_z], dim=1)
    return means + offset * (gain * level)
