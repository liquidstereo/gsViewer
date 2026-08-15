import torch

_PERSISTENCE: float = 0.6
_LACUNARITY: float = 2.0

def _octave(
    x: torch.Tensor, y: torch.Tensor, z: torch.Tensor,
    k: float, wt: float, amp: float, ph: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    fx = (
        torch.sin(k * y + 0.6 * wt + ph[0])
        * torch.cos(k * z + 1.4 * wt + ph[0])
    ) * amp
    fy = (
        torch.sin(k * z + 1.0 * wt + ph[1])
        * torch.cos(k * x + 0.5 * wt + ph[1])
    ) * amp
    fz = (
        torch.sin(k * x + 0.8 * wt + ph[2])
        * torch.cos(k * y + 1.7 * wt + ph[2])
    ) * amp
    return fx, fy, fz

def apply(
    means: torch.Tensor, t: float, level: float, gain: float,
    freq: float, speed: float, octaves: int, phases: torch.Tensor,
) -> torch.Tensor:
    x = means[:, 0]
    y = means[:, 1]
    z = means[:, 2]
    sx = torch.zeros_like(x)
    sy = torch.zeros_like(y)
    sz = torch.zeros_like(z)
    k = freq
    amp = 1.0
    for o in range(max(1, octaves)):
        wt = t * speed * (1.0 + 0.15 * o)
        ph = phases[o]
        fx, fy, fz = _octave(x, y, z, k, wt, amp, ph)
        sx = sx + fx
        sy = sy + fy
        sz = sz + fz
        k *= _LACUNARITY
        amp *= _PERSISTENCE
    offset = torch.stack([sx, sy, sz], dim=1)
    return means + offset * (gain * level)
