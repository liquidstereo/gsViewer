import torch

def apply_fog(
    splat: dict,
    viewmat: torch.Tensor,
    density: float,
    start: float,
    threshold: float,
    threshold_density: float,
) -> dict:
    vm = viewmat[0]
    R, t = vm[:3, :3], vm[:3, 3]
    cam_pos = -R.T @ t
    dist = (splat['means'] - cam_pos).norm(dim=-1)
    factor = torch.exp(-density * (dist - start).clamp(min=0.0))
    factor *= torch.exp(
        -threshold_density * (dist - threshold).clamp(min=0.0)
    )
    fogged = dict(splat)
    fogged['opacities'] = (splat['opacities'] * factor).clamp(0.0, 1.0)
    return fogged
