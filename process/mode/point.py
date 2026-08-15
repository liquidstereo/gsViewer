import logging

import torch

from configs.settings_color import MODE_POINT_COLOR
from configs.settings_effects import DILATE_SCALE, POINT_SCALE
from process.common import hex_to_rgb

logger = logging.getLogger(__name__)

def make_point_splat(splat: dict) -> tuple[dict, torch.Tensor]:
    N = splat['means'].shape[0]
    device = splat['means'].device
    point_splat = dict(splat)
    point_splat['scales'] = torch.full(
        (N, 3), POINT_SCALE * DILATE_SCALE,
        dtype=torch.float32, device=device,
    )
    r, g, b = hex_to_rgb(MODE_POINT_COLOR)
    colors = torch.tensor(
        [[r, g, b]], dtype=torch.float32, device=device,
    ).repeat(N, 1)
    logger.debug('Point mode: %d gaussians, scale=%.4f', N, POINT_SCALE)
    return point_splat, colors
