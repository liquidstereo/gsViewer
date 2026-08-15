import math

import torch

_SKEW: float = 1.0 / 3.0
_UNSKEW: float = 1.0 / 6.0

def _skew_coords(
    x: torch.Tensor, y: torch.Tensor, z: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    s = (x + y + z) * _SKEW
    return x + s, y + s, z + s

def _octave(
    sx: torch.Tensor, sy: torch.Tensor, sz: torch.Tensor,
    k: float, wt: float, amp: float, ph: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    phase = 2.0 * math.pi / 3.0
    vx = (
        torch.sin(k * sx + wt + ph[0])
        + torch.sin(k * sy + wt + phase + ph[0])
        + torch.sin(k * sz + wt + 2.0 * phase + ph[0])
    ) * amp
    vy = (
        torch.cos(k * sy + 0.6 * wt + ph[1])
        + torch.cos(k * sz + 0.6 * wt + phase + ph[1])
        + torch.cos(k * sx + 0.6 * wt + 2.0 * phase + ph[1])
    ) * amp
    vz = (
        torch.sin(k * sz - 0.3 * wt + ph[2])
        + torch.sin(k * sx - 0.3 * wt + phase + ph[2])
        + torch.sin(k * sy - 0.3 * wt + 2.0 * phase + ph[2])
    ) * amp
    return vx, vy, vz

def apply(
    means: torch.Tensor, t: float, level: float, gain: float,
    freq: float, speed: float, octaves: int, phases: torch.Tensor,
) -> torch.Tensor:
    x = means[:, 0]
    y = means[:, 1]
    z = means[:, 2]
    sx, sy, sz = _skew_coords(x, y, z)
    ax = torch.zeros_like(x)
    ay = torch.zeros_like(y)
    az = torch.zeros_like(z)
    k = freq
    amp = 1.0
    for o in range(max(1, octaves)):
        wt = t * speed * (1.0 + 0.2 * o)
        ph = phases[o]
        vx, vy, vz = _octave(sx, sy, sz, k, wt, amp, ph)
        ax = ax + vx
        ay = ay + vy
        az = az + vz
        k *= 2.0
        amp *= 0.5

    u = (ax + ay + az) * _UNSKEW
    offset = torch.stack([ax - u, ay - u, az - u], dim=1)
    return means + offset * (gain * level)
