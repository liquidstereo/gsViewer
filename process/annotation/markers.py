import logging

import numpy as np
import torch

from process.camera import viewmat_K_to_numpy

logger = logging.getLogger(__name__)

def compute_annotation_markers(
    items: list[dict],
    viewmat: torch.Tensor,
    K: torch.Tensor,
    ortho: bool = False,
) -> list[tuple[int, int, str]]:
    vm, K_np = viewmat_K_to_numpy(viewmat, K)
    result = []
    for item in items:
        pos = item['pos'].astype(np.float32)
        c = (vm @ np.append(pos, 1.0))[:3]
        if c[2] <= 0:
            continue
        if ortho:
            sx = int(K_np[0, 0] * c[0] + K_np[0, 2])
            sy = int(K_np[1, 1] * c[1] + K_np[1, 2])
        else:
            sx = int(K_np[0, 0] * c[0] / c[2] + K_np[0, 2])
            sy = int(K_np[1, 1] * c[1] / c[2] + K_np[1, 2])
        result.append((sx, sy, item['label']))
    return result
