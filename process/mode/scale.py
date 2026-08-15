import logging

import torch

from configs.settings_color import MODE_SCALE_CMAP
from process.common import apply_cmap

logger = logging.getLogger(__name__)

def compute_scale_colors(splat: dict) -> torch.Tensor:
    scales = splat['scales']
    mean_s = scales.mean(dim=1)
    s_min = mean_s.min()
    s_max = mean_s.max()
    t = (mean_s - s_min) / (s_max - s_min + 0.00000001)
    logger.debug(
        'Scale mode: range [%.4f, %.4f]',
        s_min.item(), s_max.item(),
    )
    return apply_cmap(t, MODE_SCALE_CMAP)
