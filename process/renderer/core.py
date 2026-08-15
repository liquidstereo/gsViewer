import logging
import sys
import time

import numpy as np
import torch
import gsplat

from configs.settings import SH_C0, SH_C1, SH_C2, SH_C3
from configs.settings_camera import NEAR_PLANE, FAR_PLANE
from configs.settings_window import WINDOW_WIDTH, WINDOW_HEIGHT
from configs.settings_color import BACKGROUND_COLOR
from configs.colorize import Msg
from process.common import hex_to_rgb

logger = logging.getLogger(__name__)

_cuda_warmed: bool = False
_backgrounds: torch.Tensor | None = None
_far_plane: float = FAR_PLANE

def set_far_plane(far: float) -> None:
    global _far_plane
    _far_plane = far
    logger.debug('FAR plane updated: %.2f', far)

def get_far_plane() -> float:
    return _far_plane

def _get_backgrounds() -> torch.Tensor:
    global _backgrounds
    if _backgrounds is None:
        r, g, b = hex_to_rgb(BACKGROUND_COLOR)
        _backgrounds = torch.tensor(
            [r, g, b], dtype=torch.float32, device='cuda'
        )
    return _backgrounds

def eval_sh_gpu(
    sh: torch.Tensor, dirs: torch.Tensor
) -> torch.Tensor:
    x = dirs[:, 0:1]
    y = dirs[:, 1:2]
    z = dirs[:, 2:3]
    xx, yy, zz = x * x, y * y, z * z
    xy, yz, xz = x * y, y * z, x * z
    c2, c3 = SH_C2, SH_C3
    result = (
        SH_C0 * sh[:, 0]
        - SH_C1 * y * sh[:, 1]
        + SH_C1 * z * sh[:, 2]
        - SH_C1 * x * sh[:, 3]
        + c2[0] * xy * sh[:, 4]
        + c2[1] * yz * sh[:, 5]
        + c2[2] * (2 * zz - xx - yy) * sh[:, 6]
        + c2[3] * xz * sh[:, 7]
        + c2[4] * (xx - yy) * sh[:, 8]
        + c3[0] * y * (3 * xx - yy) * sh[:, 9]
        + c3[1] * xy * z * sh[:, 10]
        + c3[2] * y * (4 * zz - xx - yy) * sh[:, 11]
        + c3[3] * z * (2 * zz - 3 * xx - 3 * yy) * sh[:, 12]
        + c3[4] * x * (4 * zz - xx - yy) * sh[:, 13]
        + c3[5] * z * (xx - yy) * sh[:, 14]
        + c3[6] * x * (xx - 3 * yy) * sh[:, 15]
    )
    return torch.clamp(result + 0.5, 0.0, 1.0)

def compute_colors(
    splat: dict, cam_pos: torch.Tensor
) -> torch.Tensor:
    dirs = torch.nn.functional.normalize(
        cam_pos[None, :] - splat['means'], p=2, dim=1
    )
    return eval_sh_gpu(splat['sh_coeffs'], dirs)

def _rasterize(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    colors: torch.Tensor,
    camera_model: str = 'pinhole',
) -> tuple[torch.Tensor, torch.Tensor]:
    global _cuda_warmed
    _t0 = 0.0
    if not _cuda_warmed:
        logger.info(
            'First gsplat.rasterization call - '
            'compiling CUDA kernels...'
        )
        _t0 = time.perf_counter()
    with torch.no_grad():
        render_colors, render_alphas, _ = gsplat.rasterization(
            means=splat['means'],
            quats=splat['quats'],
            scales=splat['scales'],
            opacities=splat['opacities'],
            colors=colors,
            viewmats=viewmat,
            Ks=K,
            width=w,
            height=h,
            near_plane=NEAR_PLANE,
            far_plane=_far_plane,
            backgrounds=_get_backgrounds(),
            camera_model=camera_model,
        )
    if not _cuda_warmed:
        logger.info(
            'CUDA kernels compiled: %.1fs',
            time.perf_counter() - _t0,
        )
        _cuda_warmed = True
    return render_colors, render_alphas

def render_frame_gpu(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    colors: torch.Tensor | None = None,
    camera_model: str = 'pinhole',
) -> torch.Tensor:
    if colors is None:
        from process.camera import cam_pos_from_viewmat
        cam_pos = cam_pos_from_viewmat(viewmat)
        colors = compute_colors(splat, cam_pos)
    rc, _ = _rasterize(
        splat, viewmat, K, w, h, colors, camera_model,
    )
    return (rc[0] * 255.0).clamp(0, 255)

def render_frame(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    colors: torch.Tensor | None = None,
    camera_model: str = 'pinhole',
) -> np.ndarray:
    rgb = render_frame_gpu(
        splat, viewmat, K, w, h, colors, camera_model,
    )
    return rgb.to(torch.uint8).cpu().numpy()

def _rasterize_with_depth(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    colors: torch.Tensor,
    camera_model: str = 'pinhole',
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    with torch.no_grad():
        render_out, render_alphas, _ = gsplat.rasterization(
            means=splat['means'],
            quats=splat['quats'],
            scales=splat['scales'],
            opacities=splat['opacities'],
            colors=colors,
            viewmats=viewmat,
            Ks=K,
            width=w,
            height=h,
            near_plane=NEAR_PLANE,
            far_plane=_far_plane,
            render_mode='RGB+ED',
            backgrounds=None,
            camera_model=camera_model,
        )
    return render_out[:, :, :, :3], render_alphas, render_out[:, :, :, 3:]

def render_frame_with_depth(
    splat: dict,
    viewmat: torch.Tensor,
    K: torch.Tensor,
    w: int,
    h: int,
    colors: torch.Tensor | None = None,
    camera_model: str = 'pinhole',
) -> tuple[np.ndarray, np.ndarray]:
    if colors is None:
        from process.camera import cam_pos_from_viewmat
        cam_pos = cam_pos_from_viewmat(viewmat)
        colors = compute_colors(splat, cam_pos)
    rc, ra, rd = _rasterize_with_depth(
        splat, viewmat, K, w, h, colors, camera_model,
    )
    bg = _get_backgrounds()
    rgb_tensor = rc[0] + (1.0 - ra[0]) * bg
    rgb = (rgb_tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    depth = rd[0, :, :, 0].cpu().numpy()
    return rgb, depth

def _theme_refresh() -> None:

    global _backgrounds
    _backgrounds = None

def warmup_renderer(
    splat: dict, cam: dict, K: torch.Tensor
) -> None:
    from process.camera import _viewmat_from_cam
    viewmat = _viewmat_from_cam(cam)
    sys.stdout.write('COMPILING CUDA SHADERS...\r')
    sys.stdout.flush()
    t0 = time.perf_counter()
    render_frame(splat, viewmat, K, WINDOW_WIDTH, WINDOW_HEIGHT)
    elapsed = time.perf_counter() - t0
    elapsed_ms = elapsed * 1000
    m, s = divmod(elapsed, 60)
    h_part, m = divmod(int(m), 60)
    time_str = f'{h_part:02d}:{m:02d}:{s:06.3f}'
    sys.stdout.write('\033[2K\r')
    sys.stdout.flush()

    Msg.Dim(f'CUDA SHADERS COMPILED IN {elapsed_ms:,.0f} ms. ({time_str})', flush=tuple)
    logger.info('CUDA warmup complete: %.1fs', elapsed)
