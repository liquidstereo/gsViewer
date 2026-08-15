import logging

import torch

from configs.settings_color import MODE_DEPTH_CMAP
from process.common import apply_cmap

logger = logging.getLogger(__name__)

def compute_depth_colors(
    splat: dict, viewmat: torch.Tensor
) -> torch.Tensor:
    means = splat['means']
    depth = means @ viewmat[0, 2, :3] + viewmat[0, 2, 3]
    d_min = depth.min()
    d_max = depth.max()
    t = (depth - d_min) / (d_max - d_min + 0.00000001)
    logger.debug(
        'Depth mode: range [%.3f, %.3f]',
        d_min.item(), d_max.item(),
    )
    return apply_cmap(t, MODE_DEPTH_CMAP)
