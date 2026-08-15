import torch

def _init_velocities(
    means: torch.Tensor, force: float
) -> torch.Tensor:
    d = torch.randn_like(means)
    d = torch.nn.functional.normalize(d, p=2, dim=-1)
    return d * force

def _integrate(
    means: torch.Tensor,
    vels: torch.Tensor,
    dt: float,
    gravity_y: float,
) -> torch.Tensor:
    g = torch.tensor([0.0, gravity_y, 0.0], device=means.device)
    return means + vels * dt + 0.5 * g * dt * dt

def _fade(
    opac: torch.Tensor, fade_rate: float, elapsed: float
) -> torch.Tensor:
    return (opac - fade_rate * elapsed).clamp(min=0.0)

def _spring_step(
    means: torch.Tensor,
    base: torch.Tensor,
    vels: torch.Tensor,
    dt: float,
    k: float,
    damping: float,
    gravity_y: float,
    vel_clamp: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    g = torch.tensor([0.0, gravity_y, 0.0], device=means.device)
    acc = k * (base - means) + g
    vels = (vels + acc * dt) * damping
    vels = vels.clamp(-vel_clamp, vel_clamp)
    means = torch.nan_to_num(means + vels * dt)
    return means, vels
