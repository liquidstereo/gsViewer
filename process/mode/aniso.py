import logging
import math

import torch

from configs.settings_color import MODE_ANISO_CMAP
from process.common import apply_cmap

_LOG_ANISO_MAX = math.log(100.0)

logger = logging.getLogger(__name__)

def compute_aniso_colors(splat: dict) -> torch.Tensor:
    scales = splat['scales']
    max_s = scales.max(dim=1).values
    min_s = scales.min(dim=1).values.clamp(min=0.00000001)
    aniso = max_s / min_s
    t = (torch.log(aniso) / _LOG_ANISO_MAX).clamp(0.0, 1.0)
    logger.debug(
        'Aniso mode: aniso range [%.2f, %.2f]',
        aniso.min().item(), aniso.max().item(),
    )
    return apply_cmap(t, MODE_ANISO_CMAP)
