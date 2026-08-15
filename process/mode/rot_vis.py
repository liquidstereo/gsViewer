import logging

import torch

logger = logging.getLogger(__name__)

def compute_rotation_colors(splat: dict) -> torch.Tensor:
    quats = splat['quats']
    colors = quats[:, 1:4].abs().clamp(0.0, 1.0)
    logger.debug('Rotation mode: %d gaussians', quats.shape[0])
    return colors
