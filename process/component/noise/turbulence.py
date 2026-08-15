import torch

def _octave(
    x: torch.Tensor, y: torch.Tensor, z: torch.Tensor,
    k: float, wt: float, amp: float, ph: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    tx = torch.abs(
        torch.sin(k * y + wt + ph[0])
        - torch.cos(k * z - 0.6 * wt + ph[0])
    ) * amp
    ty = torch.abs(
        torch.sin(k * z + 1.1 * wt + ph[1])
        - torch.cos(k * x - 0.4 * wt + ph[1])
    ) * amp
    tz = torch.abs(
        torch.sin(k * x + 0.7 * wt + ph[2])
        - torch.cos(k * y - 1.3 * wt + ph[2])
    ) * amp
    return tx, ty, tz

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
        wt = t * speed * (1.0 + 0.25 * o)
        ph = phases[o]
        tx, ty, tz = _octave(x, y, z, k, wt, amp, ph)
        sx = sx + tx
        sy = sy + ty
        sz = sz + tz
        k *= 2.0
        amp *= 0.5
    offset = torch.stack([sx, sy, sz], dim=1)

    offset = offset - offset.mean(dim=0, keepdim=True)
    return means + offset * (gain * level)
