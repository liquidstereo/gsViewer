import logging
import math
from pathlib import Path

import numpy as np
import torch

from configs.settings_camera import (
    WORLD_ROT, WORLD_ROT_PRESETS, WORLD_ROT_NAMES,
    CAM_DIST_FACTOR, CAM_FOCAL_LENGTH, CAM_ZOOM, CAM_DOLLY,
    FOV_X_DEG, EL_CLAMP, FAR_PLANE, STARTUP_CAM_POSITION,
    STARTUP_CAM_DEGREE,
)
from process.renderer.core import set_far_plane

logger = logging.getLogger(__name__)

_FLIP_MAT = np.array(WORLD_ROT, dtype=np.float32)
_FLIP4 = np.eye(4, dtype=np.float32)
_FLIP4[:3, :3] = _FLIP_MAT

_GIZMO_POS_TO_DISPLAY = np.array([1.0, -1.0, -1.0], dtype=np.float32)

_rot_idx: int = 0

def cycle_world_rot() -> tuple[np.ndarray, np.ndarray, int]:
    global _rot_idx
    old_mat = _FLIP_MAT.copy()
    _rot_idx = (_rot_idx + 1) % len(WORLD_ROT_PRESETS)
    new_mat = np.array(WORLD_ROT_PRESETS[_rot_idx], dtype=np.float32)
    _FLIP_MAT[:] = new_mat
    _FLIP4[:3, :3] = new_mat
    logger.info(
        'WORLD_ROT -> %s (idx=%d)', WORLD_ROT_NAMES[_rot_idx], _rot_idx
    )
    return old_mat, new_mat, _rot_idx

_SOG_ROT_IDX: int = 3

def set_world_rot_preset(idx: int) -> tuple[np.ndarray, int]:
    global _rot_idx
    _rot_idx = idx % len(WORLD_ROT_PRESETS)
    new_mat = np.array(WORLD_ROT_PRESETS[_rot_idx], dtype=np.float32)
    _FLIP_MAT[:] = new_mat
    _FLIP4[:3, :3] = new_mat
    logger.info(
        'WORLD_ROT set -> %s (idx=%d)',
        WORLD_ROT_NAMES[_rot_idx], _rot_idx,
    )
    return new_mat, _rot_idx

def auto_apply_world_rot(files: list[Path]) -> None:
    if not files:
        return
    suffix = files[0].suffix.lower()
    target = _SOG_ROT_IDX if suffix in {'.sog', '.spz'} else 0
    if target == _rot_idx:
        return
    set_world_rot_preset(target)

def viewmat_from_pos_target(
    pos: np.ndarray, target: np.ndarray,
) -> torch.Tensor:
    eye = pos.astype(np.float32)
    z = target.astype(np.float32) - eye
    z = z / np.linalg.norm(z)
    world_dn = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    x = np.cross(world_dn, z)
    if np.linalg.norm(x) < 0.000001:
        world_dn = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        x = np.cross(world_dn, z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.stack([x, y, z]).astype(np.float32)
    t = (-R @ eye).astype(np.float32)
    mat = np.eye(4, dtype=np.float32)
    mat[:3, :3] = R
    mat[:3, 3] = t
    return torch.tensor(mat @ _FLIP4, device='cuda').unsqueeze(0)

def resolve_initial_camera(radius: float) -> tuple[float, float]:
    if isinstance(CAM_DOLLY, str) and CAM_DOLLY.lower() == 'auto':
        distance = radius * CAM_DIST_FACTOR
    else:
        distance = float(CAM_DOLLY)
    fx_scale = float(CAM_ZOOM)
    return distance, fx_scale

_QUANTILE_MAX_ELEMS = 1 << 24

def _robust_radius(dists: torch.Tensor, q: float = 0.95) -> float:
    n = dists.numel()
    if n > _QUANTILE_MAX_ELEMS:
        stride = (n + _QUANTILE_MAX_ELEMS - 1) // _QUANTILE_MAX_ELEMS
        dists = dists[::stride]
        logger.info(
            'quantile downsample: %d -> %d (stride=%d)',
            n, dists.numel(), stride,
        )
    return float(dists.quantile(q).item())

def init_cam_state(means: torch.Tensor) -> dict:
    center = means.mean(dim=0)
    dists = torch.norm(means - center, dim=1)
    radius = _robust_radius(dists)
    cx, cy, cz = (
        center[0].item(), center[1].item(), center[2].item()
    )
    target = _FLIP_MAT @ np.array(
        [cx, cy, cz], dtype=np.float32
    ) + (
        np.array(STARTUP_CAM_POSITION, dtype=np.float32)
        * _GIZMO_POS_TO_DISPLAY
    )
    dolly, fx_scale = resolve_initial_camera(radius)
    far = max(FAR_PLANE, (dolly + radius) * 2.0)
    set_far_plane(far)
    logger.info(
        'Camera init: center=(%.2f,%.2f,%.2f) radius=%.2f'
        ' dolly=%.3f zoom=%.3f far=%.2f',
        cx, cy, cz, radius, dolly, fx_scale, far,
    )
    return {
        'target': target.astype(np.float64),
        'distance': dolly,
        'azimuth': math.radians(STARTUP_CAM_DEGREE),
        'elevation': 0.0,
        'fx_scale': fx_scale,
    }

def _viewmat_from_cam(cam: dict) -> torch.Tensor:
    tgt = cam['target']
    dist = cam['distance']
    az = cam['azimuth']
    el = float(np.clip(cam['elevation'], -EL_CLAMP, EL_CLAMP))

    eye = tgt + np.array([
        -dist * math.sin(az) * math.cos(el),
        -dist * math.sin(el),
        -dist * math.cos(az) * math.cos(el),
    ])
    z = tgt - eye
    z = z / np.linalg.norm(z)

    world_dn = np.array([0.0, 1.0, 0.0])
    x = np.cross(world_dn, z)
    if np.linalg.norm(x) < 0.000001:
        world_dn = np.array([0.0, 0.0, 1.0])
        x = np.cross(world_dn, z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)

    R = np.stack([x, y, z]).astype(np.float32)
    t = (-R @ eye).astype(np.float32)
    mat = np.eye(4, dtype=np.float32)
    mat[:3, :3] = R
    mat[:3, 3] = t
    return torch.tensor(
        mat @ _FLIP4, device='cuda'
    ).unsqueeze(0)

def cam_pos_from_viewmat(
    viewmat: torch.Tensor
) -> torch.Tensor:
    mat = viewmat_to_numpy(viewmat)
    pos = -(mat[:3, :3].T @ mat[:3, 3])
    return torch.tensor(pos, dtype=torch.float32, device='cuda')

def viewmat_to_numpy(viewmat: torch.Tensor) -> np.ndarray:
    return viewmat[0].cpu().numpy()

def viewmat_K_to_numpy(
    viewmat: torch.Tensor, K: torch.Tensor,
) -> tuple[np.ndarray, np.ndarray]:
    return viewmat[0].cpu().numpy(), K[0].cpu().numpy()

def init_camera_from_splat(
    splat: dict, w: int, h: int
) -> tuple[dict, torch.Tensor]:
    cam = init_cam_state(splat['means'])
    _, K = build_camera(cam, w, h)
    return cam, K

def build_K(
    cam: dict, w: int, h: int, ortho: bool = False,
) -> torch.Tensor:
    _is_auto_focal = (
        CAM_FOCAL_LENGTH is None
        or (
            isinstance(CAM_FOCAL_LENGTH, str)
            and CAM_FOCAL_LENGTH.lower() == 'auto'
        )
    )
    if _is_auto_focal:
        fov_x = math.radians(FOV_X_DEG)
        fx = w / (2.0 * math.tan(fov_x / 2.0))
    else:
        fx = float(CAM_FOCAL_LENGTH)

    fx *= float(cam.get('fx_scale', 1.0))
    if ortho:
        d = max(float(cam['distance']), 0.000001)
        fx = fx / d
    K = torch.tensor(
        [
            [fx, 0.0, w / 2.0],
            [0.0, fx, h / 2.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=torch.float32, device='cuda',
    ).unsqueeze(0)
    return K

def build_camera(
    cam: dict, w: int, h: int, ortho: bool = False,
) -> tuple[torch.Tensor, torch.Tensor]:
    viewmat = _viewmat_from_cam(cam)
    K = build_K(cam, w, h, ortho=ortho)
    return viewmat, K
