import logging
from enum import IntEnum

import torch

from configs.settings_window import STARTUP_MODE

logger = logging.getLogger(__name__)

from process.mode.normal import compute_normal_colors
from process.mode.point import make_point_splat
from process.mode.aniso import compute_aniso_colors
from process.mode.opac import compute_opacity_colors
from process.mode.depth import compute_depth_colors
from process.mode.scale import compute_scale_colors
from process.mode.sh_vis import compute_sh_colors
from process.mode.rot_vis import compute_rotation_colors

class RenderMode(IntEnum):
    DEFAULT = 0
    NORMAL = 1
    POINT = 2
    ANISO = 3
    OPACITY = 4
    DEPTH = 5
    ACCUMULATION = 6
    SCALE = 7
    SH = 8
    ROTATION = 9
    GRADIENTS = 10
    HIT_COUNT = 11
    MEDIAN_DEPTH = 12
    GL_POINTS = 13

MODE_NAMES: dict[int, str] = {
    0: 'Default (SH)',
    1: 'Normal',
    2: 'Point',
    3: 'Anisotropy',
    4: 'Opacity',
    5: 'Depth',
    6: 'Accumulation (Alpha)',
    7: 'Scale',
    8: 'Spherical Harmonics',
    9: 'Rotation',
    10: 'Gradients',
    11: 'Hit Count',
    12: 'Median Depth',
    13: 'Point Cloud (GL)',
}

_STARTUP_MODE_MAP: dict[str, 'RenderMode'] = {
    'Default':      RenderMode.DEFAULT,
    'Normal':       RenderMode.NORMAL,
    'Point':        RenderMode.POINT,
    'Aniso':        RenderMode.ANISO,
    'Opacity':      RenderMode.OPACITY,
    'Depth':        RenderMode.DEPTH,
    'Accumulation': RenderMode.ACCUMULATION,
    'Scale':        RenderMode.SCALE,
    'SH':           RenderMode.SH,
    'Rotation':     RenderMode.ROTATION,
    'Gradients':    RenderMode.GRADIENTS,
    'HitCount':     RenderMode.HIT_COUNT,
    'MedianDepth':  RenderMode.MEDIAN_DEPTH,
    'PointCloud':   RenderMode.GL_POINTS,
}

_STARTUP_LOWER_MAP: dict[str, 'RenderMode'] = {
    k.lower(): v for k, v in _STARTUP_MODE_MAP.items()
}

STARTUP_MODE_CHOICES: tuple[str, ...] = tuple(_STARTUP_LOWER_MAP)

_STARTUP_OVERRIDE: 'RenderMode | None' = None

def mode_from_name(name: str) -> 'RenderMode':
    mode = _STARTUP_MODE_MAP.get(name)
    if mode is None:
        logger.warning(
            'Unknown STARTUP_MODE %r -- falling back to Default', name
        )
        return RenderMode.DEFAULT
    return mode

def configure_startup_mode(name: str | None) -> None:
    global _STARTUP_OVERRIDE
    if not name:
        return
    mode = _STARTUP_LOWER_MAP.get(name.lower())
    if mode is None:
        logger.warning(
            'Unknown --mode %r -- using settings STARTUP_MODE', name
        )
        return
    _STARTUP_OVERRIDE = mode

def startup_mode() -> 'RenderMode':
    if _STARTUP_OVERRIDE is not None:
        return _STARTUP_OVERRIDE
    return mode_from_name(STARTUP_MODE)

_PIXEL_MODES: frozenset = frozenset({
    RenderMode.ACCUMULATION,
    RenderMode.GRADIENTS,
    RenderMode.HIT_COUNT,
    RenderMode.MEDIAN_DEPTH,
})

HICONTRAST_OVERLAY_MODES: frozenset = frozenset({
    RenderMode.ACCUMULATION,
    RenderMode.HIT_COUNT,
})

def apply_render_mode(
    splat: dict,
    mode: 'RenderMode',
    viewmat: torch.Tensor | None = None,
) -> tuple[dict, torch.Tensor | None]:
    if mode == RenderMode.DEFAULT:
        return splat, None
    if mode == RenderMode.NORMAL:
        return splat, compute_normal_colors(splat)
    if mode == RenderMode.POINT:
        p_splat, colors = make_point_splat(splat)
        return p_splat, colors
    if mode == RenderMode.ANISO:
        return splat, compute_aniso_colors(splat)
    if mode == RenderMode.OPACITY:
        return splat, compute_opacity_colors(splat)
    if mode == RenderMode.DEPTH:
        return splat, compute_depth_colors(splat, viewmat)
    if mode == RenderMode.SCALE:
        return splat, compute_scale_colors(splat)
    if mode == RenderMode.SH:
        return splat, compute_sh_colors(splat)
    if mode == RenderMode.ROTATION:
        return splat, compute_rotation_colors(splat)
    return splat, None
