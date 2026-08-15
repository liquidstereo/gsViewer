import logging

import numpy as np
import torch

logger = logging.getLogger(__name__)

def compute_region_volume_keyframe_markers(
    items: list[dict],
    viewmat: torch.Tensor,
    K: torch.Tensor,
    ortho: bool = False,
) -> list[tuple[int, int, str]]:
    vm = viewmat[0].cpu().numpy()
    K_np = K[0].cpu().numpy()
    result: list[tuple[int, int, str]] = []
    for item in items:
        center = np.asarray(item['center'], dtype=np.float32)
        c = (vm @ np.append(center, 1.0))[:3]
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
