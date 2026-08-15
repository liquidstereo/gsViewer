import logging

import numpy as np
import torch
import gsplat

from configs.settings_camera import NEAR_PLANE
from configs.settings_color import (
    BACKGROUND_COLOR,
    MODE_ACCUM_CMAP, MODE_MEDIAN_DEPTH_CMAP, MODE_HIT_COUNT_CMAP,
)
from process.common import hex_to_rgb, _cmap_fallback
from process.renderer.core import (
    _get_backgrounds, render_frame, get_far_plane,
)

logger = logging.getLogger(__name__)

_bg_np: np.ndarray | None = None
_BLACK_BG: np.ndarray = np.zeros(3, dtype=np.float32)
_HIT_PROBE_OPACITY: float = 1.0 / 64.0

def _get_bg_np() -> np.ndarray:
    global _bg_np
    if _bg_np is None:
        _bg_np = np.array(hex_to_rgb(BACKGROUND_COLOR), dtype=np.float32)
    return _bg_np

def _theme_refresh() -> None:

    global _bg_np
    _bg_np = None

def _apply_cmap_np(t: np.ndarray, cmap_name: str) -> np.ndarray:
    try:
        import matplotlib.cm as mcm
        return mcm.get_cmap(cmap_name)(t)[:, :, :3].astype(np.float32)
    except ImportError:
        return _cmap_fallback(t, cmap_name)

def _apply_pixel_mode_bg(
    colormap_rgb: np.ndarray,
    coverage: np.ndarray,
    bg: np.ndarray | None = None,
) -> np.ndarray:
    resolved_bg = bg if bg is not None else _get_bg_np()
    blended = (
        colormap_rgb * coverage[:, :, None]
        + resolved_bg * (1.0 - coverage[:, :, None])
    )
    return (blended * 255.0).clip(0, 255).astype(np.uint8)

def render_frame_accumulation(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    camera_model: str = 'pinhole',
) -> np.ndarray:
    N = splat['means'].shape[0]
    device = splat['means'].device
    white = torch.ones(N, 3, dtype=torch.float32, device=device)
    with torch.no_grad():
        _, ra, _ = gsplat.rasterization(
            means=splat['means'],
            quats=splat['quats'],
            scales=splat['scales'],
            opacities=splat['opacities'],
            colors=white,
            viewmats=viewmat,
            Ks=K,
            width=w,
            height=h,
            near_plane=NEAR_PLANE,
            far_plane=get_far_plane(),
            backgrounds=_get_backgrounds(),
            camera_model=camera_model,
        )
    alpha = ra[0, :, :, 0].cpu().numpy()
    rgb = _apply_cmap_np(alpha, MODE_ACCUM_CMAP)
    return _apply_pixel_mode_bg(rgb, alpha, _BLACK_BG)

def render_frame_median_depth(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    camera_model: str = 'pinhole',
) -> np.ndarray:
    N = splat['means'].shape[0]
    device = splat['means'].device
    white = torch.ones(N, 3, dtype=torch.float32, device=device)
    with torch.no_grad():
        render_out, render_alphas, _ = gsplat.rasterization(
            means=splat['means'],
            quats=splat['quats'],
            scales=splat['scales'],
            opacities=splat['opacities'],
            colors=white,
            viewmats=viewmat,
            Ks=K,
            width=w,
            height=h,
            near_plane=NEAR_PLANE,
            far_plane=get_far_plane(),
            render_mode='RGB+ED',
            backgrounds=None,
            camera_model=camera_model,
        )
    depth = render_out[0, :, :, 3].cpu().numpy()
    alpha = render_alphas[0, :, :, 0].cpu().numpy()
    valid = depth[alpha > 0.0001]
    if valid.size == 0:
        return _apply_pixel_mode_bg(
            np.zeros((h, w, 3), dtype=np.float32), alpha
        )
    d_min, d_max = valid.min(), valid.max()
    t = np.clip((depth - d_min) / (d_max - d_min + 0.00000001), 0.0, 1.0)
    rgb = _apply_cmap_np(t, MODE_MEDIAN_DEPTH_CMAP)
    return _apply_pixel_mode_bg(rgb, alpha)

def render_frame_hit_count(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    camera_model: str = 'pinhole',
) -> np.ndarray:
    N = splat['means'].shape[0]
    device = splat['means'].device
    white = torch.ones(N, 3, dtype=torch.float32, device=device)
    probe_opac = torch.full(
        (N,), _HIT_PROBE_OPACITY, dtype=torch.float32, device=device
    )
    with torch.no_grad():
        _, ra, _ = gsplat.rasterization(
            means=splat['means'],
            quats=splat['quats'],
            scales=splat['scales'],
            opacities=probe_opac,
            colors=white,
            viewmats=viewmat,
            Ks=K,
            width=w,
            height=h,
            near_plane=NEAR_PLANE,
            far_plane=get_far_plane(),
            backgrounds=_get_backgrounds(),
            camera_model=camera_model,
        )
    alpha = ra[0, :, :, 0].cpu().numpy()
    hit = -np.log1p(-alpha.clip(0.0, 1.0 - 0.000001)) / _HIT_PROBE_OPACITY
    valid = hit[hit > 0]
    if valid.size == 0:
        return _apply_pixel_mode_bg(
            np.zeros((h, w, 3), dtype=np.float32), alpha, _BLACK_BG
        )
    p95 = float(np.percentile(valid, 95))
    t = np.clip(hit / (p95 + 0.00000001), 0.0, 1.0)
    rgb = _apply_cmap_np(t, MODE_HIT_COUNT_CMAP)
    return _apply_pixel_mode_bg(rgb, alpha, _BLACK_BG)

def render_frame_pixel_mode(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    mode,
    camera_model: str = 'pinhole',
) -> np.ndarray:
    from process.mode import RenderMode
    if mode == RenderMode.ACCUMULATION:
        return render_frame_accumulation(
            splat, viewmat, K, w, h, camera_model,
        )
    if mode == RenderMode.MEDIAN_DEPTH:
        return render_frame_median_depth(
            splat, viewmat, K, w, h, camera_model,
        )
    if mode == RenderMode.HIT_COUNT:
        return render_frame_hit_count(
            splat, viewmat, K, w, h, camera_model,
        )
    if mode == RenderMode.GRADIENTS:
        from process.mode.opac import compute_opacity_colors
        logger.warning(
            'GRADIENTS unavailable in inference; substituting Opacity mode'
        )
        return render_frame(
            splat, viewmat, K, w, h,
            colors=compute_opacity_colors(splat),
            camera_model=camera_model,
        )
    logger.warning('Pixel mode %s not yet implemented', mode.name)
    return _apply_pixel_mode_bg(
        np.zeros((h, w, 3), dtype=np.float32),
        np.zeros((h, w), dtype=np.float32),
    )
