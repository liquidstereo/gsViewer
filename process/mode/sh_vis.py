import logging

import torch

from configs.settings_color import MODE_SH_CMAP
from process.common import apply_cmap

logger = logging.getLogger(__name__)

def compute_sh_colors(splat: dict) -> torch.Tensor:
    sh = splat['sh_coeffs']
    if sh.shape[1] > 1:
        higher = sh[:, 1:, :]
        intensity = higher.norm(dim=(1, 2))
    else:
        intensity = sh[:, 0, :].norm(dim=1)
    i_min = intensity.min()
    i_max = intensity.max()
    t = (intensity - i_min) / (i_max - i_min + 0.00000001)
    logger.debug(
        'SH mode: intensity range [%.4f, %.4f]',
        i_min.item(), i_max.item(),
    )
    return apply_cmap(t, MODE_SH_CMAP)
