import logging
import time

import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

_BLUR_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

_KERNEL_CACHE: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}

def _gaussian_kernel_1d(radius: int) -> torch.Tensor:
    sigma = max(radius / 3.0, 0.5)
    x = torch.arange(-radius, radius + 1, dtype=torch.float32)
    k = torch.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()

def _blur_kernels(radius: int) -> tuple[torch.Tensor, torch.Tensor]:
    cached = _KERNEL_CACHE.get(radius)
    if cached is not None:
        return cached
    k = _gaussian_kernel_1d(radius).to(_BLUR_DEVICE)
    kh = k.view(1, 1, 1, -1).repeat(3, 1, 1, 1)
    kv = k.view(1, 1, -1, 1).repeat(3, 1, 1, 1)
    _KERNEL_CACHE[radius] = (kh, kv)
    return kh, kv

def _np_to_t(arr: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(arr.astype(np.float32)).to(_BLUR_DEVICE)

def tensor_to_uint8(t: torch.Tensor) -> np.ndarray:
    return (t.clamp(0, 255).to(torch.uint8)
            .contiguous().cpu().numpy())

def _gaussian_blur_t(t: torch.Tensor, radius: int) -> torch.Tensor:
    if radius < 1:
        return t
    t0 = time.perf_counter()
    kh, kv = _blur_kernels(radius)
    x = t.permute(2, 0, 1).unsqueeze(0)
    x = F.pad(x, (radius, radius, 0, 0), mode='reflect')
    x = F.conv2d(x, kh, groups=3)
    x = F.pad(x, (0, 0, radius, radius), mode='reflect')
    x = F.conv2d(x, kv, groups=3)
    out = x.squeeze(0).permute(1, 2, 0)
    logger.debug(
        'Gaussian blur (%s) radius=%d in %.4fs',
        _BLUR_DEVICE, radius, time.perf_counter() - t0,
    )
    return out

def apply_exposure_t(t: torch.Tensor, exposure: float) -> torch.Tensor:
    return (t * exposure).clamp(0, 255)

def apply_sharpen_t(
    t: torch.Tensor, amount: float, radius: int
) -> torch.Tensor:
    blurred = _gaussian_blur_t(t, radius)
    return (t + amount * (t - blurred)).clamp(0, 255)

def apply_bloom_t(
    t: torch.Tensor, threshold: float, intensity: float, radius: int
) -> torch.Tensor:
    bright = (t - threshold).clamp(0, 255)
    blurred = _gaussian_blur_t(bright, radius)
    return (t + intensity * blurred).clamp(0, 255)

def apply_toon_t(t: torch.Tensor, steps: int) -> torch.Tensor:
    if steps < 2:
        return t
    scale = 255.0 / (steps - 1)
    return (torch.round(t / scale) * scale).clamp(0, 255)

def apply_dof_t(
    t: torch.Tensor,
    depth_t: torch.Tensor,
    focus_dist: float,
    aperture: float,
    max_blur: int,
) -> torch.Tensor:
    coc = ((depth_t - focus_dist).abs() * aperture
           / depth_t.clamp_min(0.000001))
    blend = coc.clamp(0, 1).unsqueeze(-1)
    radius = max(1, max_blur // 2)
    blurred = _gaussian_blur_t(t, radius)
    logger.debug(
        'DoF: focus=%.2f aperture=%.3f max_blur=%d',
        focus_dist, aperture, max_blur,
    )
    return ((1.0 - blend) * t + blend * blurred).clamp(0, 255)

def apply_sharpen(
    arr: np.ndarray, amount: float, radius: int
) -> np.ndarray:
    return tensor_to_uint8(
        apply_sharpen_t(_np_to_t(arr), amount, radius)
    )

def apply_bloom(
    arr: np.ndarray,
    threshold: int,
    intensity: float,
    radius: int,
) -> np.ndarray:
    return tensor_to_uint8(
        apply_bloom_t(_np_to_t(arr), threshold, intensity, radius)
    )

def apply_toon(arr: np.ndarray, steps: int) -> np.ndarray:
    return tensor_to_uint8(apply_toon_t(_np_to_t(arr), steps))

def apply_dof(
    arr: np.ndarray,
    depth: np.ndarray,
    focus_dist: float,
    aperture: float,
    max_blur: int,
) -> np.ndarray:
    depth_t = torch.from_numpy(
        depth.astype(np.float32)
    ).to(_BLUR_DEVICE)
    return tensor_to_uint8(
        apply_dof_t(
            _np_to_t(arr), depth_t, focus_dist, aperture, max_blur,
        )
    )
