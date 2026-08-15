import logging

import torch

logger = logging.getLogger(__name__)

def _quat_to_rot(quats: torch.Tensor) -> torch.Tensor:
    w = quats[:, 0]
    x = quats[:, 1]
    y = quats[:, 2]
    z = quats[:, 3]
    r00 = 1 - 2 * (y * y + z * z)
    r01 = 2 * (x * y - w * z)
    r02 = 2 * (x * z + w * y)
    r10 = 2 * (x * y + w * z)
    r11 = 1 - 2 * (x * x + z * z)
    r12 = 2 * (y * z - w * x)
    r20 = 2 * (x * z - w * y)
    r21 = 2 * (y * z + w * x)
    r22 = 1 - 2 * (x * x + y * y)
    row0 = torch.stack([r00, r01, r02], dim=1)
    row1 = torch.stack([r10, r11, r12], dim=1)
    row2 = torch.stack([r20, r21, r22], dim=1)
    return torch.stack([row0, row1, row2], dim=1)

def compute_normal_colors(splat: dict) -> torch.Tensor:
    scales = splat['scales']
    quats = splat['quats']
    N = scales.shape[0]
    min_idx = torch.argmin(scales, dim=1)
    R = _quat_to_rot(quats)
    idx = torch.arange(N, device=R.device)
    normals = R[idx, :, min_idx]
    colors = ((normals + 1.0) * 0.5).clamp(0.0, 1.0)
    logger.debug('Normal mode: %d gaussians', N)
    return colors
