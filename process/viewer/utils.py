import logging
from pathlib import Path

import psutil
import torch
from PySide6.QtGui import QImage

from configs.system_resources import get_gpu_info

logger = logging.getLogger(__name__)

def write_image_to_file(
    img: 'QImage', out: Path, quality: int = -1,
) -> None:
    img.save(str(out), None, quality)
    logger.info('Auto-saved: %s', out)

def log_resources(label: str) -> None:
    mem = psutil.virtual_memory()
    alloc = torch.cuda.memory_allocated() / (1024 ** 3)
    resv = torch.cuda.memory_reserved() / (1024 ** 3)
    g = get_gpu_info()
    ram = (
        f'RAM {mem.used / (1024 ** 3):.2f}/'
        f'{mem.total / (1024 ** 3):.2f}GB ({mem.percent:.1f}%)'
    )
    vram = (
        f'VRAM {g["vram_used_gb"]:.2f}/{g["vram_total_gb"]:.2f}GB'
        if g else 'VRAM N/A'
    )
    torch_mem = f'Torch alloc/reserved {alloc:.2f}/{resv:.2f}GB'
    logger.info('%s | %s | %s | %s', label, ram, vram, torch_mem)
