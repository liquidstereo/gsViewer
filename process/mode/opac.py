import logging

import torch

logger = logging.getLogger(__name__)

def compute_opacity_colors(splat: dict) -> torch.Tensor:
    opacities = splat['opacities']
    gray = opacities.unsqueeze(1).expand(-1, 3).contiguous()
    logger.debug(
        'Opacity mode: alpha range [%.3f, %.3f]',
        opacities.min().item(), opacities.max().item(),
    )
    return gray
