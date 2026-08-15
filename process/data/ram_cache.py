import logging

import psutil
import torch

from configs.settings import (
    CPU_SPLAT_CACHE_RAM_FRACTION, RAM_AVAIL_FALLBACK_GB)

logger = logging.getLogger(__name__)

def upload_to_gpu(splat: dict) -> dict:
    out: dict = {}
    for k, v in splat.items():
        if isinstance(v, torch.Tensor) and not v.is_cuda:
            out[k] = v.to('cuda', non_blocking=True)
        else:
            out[k] = v
    return out

def splat_nbytes(splat: dict) -> int:
    total = 0
    for v in splat.values():
        if isinstance(v, torch.Tensor):
            total += v.element_size() * v.nelement()
    return total

def auto_cpu_budget_frames(bytes_per_frame: int) -> int:
    if bytes_per_frame <= 0:
        return 1
    try:
        avail = psutil.virtual_memory().available
    except (OSError, psutil.Error):
        avail = RAM_AVAIL_FALLBACK_GB * (1024 ** 3)
    return max(1, int(avail * CPU_SPLAT_CACHE_RAM_FRACTION / bytes_per_frame))

def forward_window(head: int, n: int, size: int) -> set:
    size = max(1, min(size, n))
    return set((head + i) % n for i in range(size))

def centered_window(head: int, n: int, radius: int) -> set:
    span = 2 * max(0, radius) + 1
    if span >= n:
        return set(range(n))
    return set((head - radius + i) % n for i in range(span))

def nearest_first(idxs: set, head: int, n: int) -> list:
    return sorted(idxs, key=lambda k: min((k - head) % n, (head - k) % n))
