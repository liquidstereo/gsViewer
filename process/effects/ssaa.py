import logging

import numpy as np
import torch

from process.renderer.core import render_frame

logger = logging.getLogger(__name__)

def _downsample(arr: np.ndarray, scale: int) -> np.ndarray:
    h, w = arr.shape[:2]
    h2, w2 = h // scale, w // scale
    crop = arr[:h2 * scale, :w2 * scale]
    return (crop
            .reshape(h2, scale, w2, scale, 3)
            .mean(axis=(1, 3))
            .astype(np.uint8))

def render_frame_ssaa(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    scale: int,
    colors: torch.Tensor | None = None,
    camera_model: str = 'pinhole',
) -> np.ndarray:
    k_hi = K.clone()
    k_hi[0, 0, 0] *= scale
    k_hi[0, 1, 1] *= scale
    k_hi[0, 0, 2] *= scale
    k_hi[0, 1, 2] *= scale
    arr_hi = render_frame(
        splat, viewmat, k_hi,
        w * scale, h * scale, colors,
        camera_model=camera_model,
    )
    arr = _downsample(arr_hi, scale)
    logger.debug(
        'SSAA x%d: %dx%d -> %dx%d',
        scale, w * scale, h * scale, w, h,
    )
    return arr
