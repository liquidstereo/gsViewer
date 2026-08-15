import logging
import os
import time

import numpy as np

_GPU_PROFILE = os.environ.get('GSVIEWER_PERF_GPU') == '1'

from configs.settings_window import FPS_ALPHA
from configs.settings_overlay import PRESERVE_SEQUENCE_OVERLAY_DURATION
from configs.settings_effects import (
    EXPOSURE, GLOBAL_OPACITY,
    FOG_DENSITY, FOG_START, FOG_THRESHOLD,
    FOG_THRESHOLD_DENSITY, FOG_POINT_BG_DENSITY, POINT_FOG_ENABLED,
    SSAA_SCALE,
    DOF_ENABLED, DOF_FOCUS_DIST, DOF_APERTURE, DOF_MAX_BLUR,
    SHARPEN_ENABLED, SHARPEN_AMOUNT, SHARPEN_RADIUS,
    BLOOM_ENABLED, BLOOM_THRESHOLD, BLOOM_INTENSITY, BLOOM_RADIUS,
    TOON_ENABLED, TOON_STEPS,
    CLIP_ENABLED, CLIP_AXIS, CLIP_MIN, CLIP_MAX,
)
from process.effects.fog import apply_fog
from process.effects.clip import apply_clipping
from process.effects.ssaa import render_frame_ssaa
from process.effects.post import (
    apply_dof, apply_sharpen, apply_bloom, apply_toon,
    apply_exposure_t, apply_sharpen_t, apply_bloom_t, apply_toon_t,
    tensor_to_uint8,
)
from process.keys.bbox_grid import compute_bbox_grid
from process.mode import (
    RenderMode, apply_render_mode, _PIXEL_MODES,
)
from process.renderer.core import (
    render_frame_gpu, render_frame_with_depth,
)
from process.renderer.pixel import render_frame_pixel_mode
from process.data.pointcloud_buffer import (
    is_pointcloud_splat, with_device_means,
)
from process.data.pointcloud_caps import cloud_processors
from process.viewer.render_glpoints import render_gl_points_frame
from process.overlay_coord import compute_gizmo_axes
from process.sequence.overlay_index import seq_overlay_index
from process.viewer.render_helpers import (
    _apply_scale_mult, _sync_ts, _update_overlay_channels,
)
from process.perf.collector import fps_tick, perf_push

logger = logging.getLogger(__name__)

def run_frame_processors(win, splat_src: dict, is_cloud: bool) -> dict:
    procs = (cloud_processors(win)[0] if is_cloud
             else win._frame_processors)
    if is_cloud and procs:
        splat_src = with_device_means(splat_src)
    for proc in procs:
        splat_src = proc(splat_src)
    return splat_src

def render_current_impl(win) -> None:
    _t_start = time.perf_counter()

    _is_cloud = is_pointcloud_splat(win._splat)
    _is_point = win._render_mode == RenderMode.POINT
    _point_fog_active = (
        _is_point
        and win._fog_point_bg
        and (POINT_FOG_ENABLED or win._fog_enabled)
    )
    if _is_cloud:
        splat_src = win._splat
    elif _point_fog_active:
        d = win._cam['distance']
        splat_src = apply_fog(
            win._splat, win._viewmat,
            0.0, d, d, FOG_POINT_BG_DENSITY,
        )
    elif win._fog_enabled:
        splat_src = apply_fog(
            win._splat, win._viewmat,
            FOG_DENSITY, FOG_START,
            FOG_THRESHOLD, FOG_THRESHOLD_DENSITY,
        )
    else:
        splat_src = win._splat
    if GLOBAL_OPACITY != 1.0 and not _is_cloud:
        if splat_src is win._splat:
            splat_src = dict(splat_src)
        splat_src['opacities'] = (
            splat_src['opacities'] * GLOBAL_OPACITY
        ).clamp(0.0, 1.0)
    if CLIP_ENABLED and not _is_cloud:
        splat_src = apply_clipping(
            splat_src, CLIP_AXIS, CLIP_MIN, CLIP_MAX
        )
    splat_src = run_frame_processors(win, splat_src, _is_cloud)
    _t_proc = time.perf_counter()
    _dbg = logger.isEnabledFor(logging.DEBUG)
    _t_raster = _t_post = _t_read = 0.0
    depth: np.ndarray | None = None
    rgb_t = None
    cam_model = win._camera_model
    _scale_mult = win._scale_mult
    if win._render_mode == RenderMode.GL_POINTS:
        arr = render_gl_points_frame(win, splat_src)
        win._widget.set_depth_buffer(None)
    elif win._render_mode in _PIXEL_MODES:
        arr = render_frame_pixel_mode(
            _apply_scale_mult(splat_src, _scale_mult), win._viewmat,
            win._K, win._w, win._h, win._render_mode,
            camera_model=cam_model,
        )
        win._widget.set_depth_buffer(None)
    else:
        if win._render_mode == RenderMode.DEFAULT:
            colors = (
                win._splat.get('colors')
                if not win._cam_dirty else None
            )
            splat = splat_src
        else:
            splat, colors = apply_render_mode(
                splat_src, win._render_mode, win._viewmat
            )
        splat = _apply_scale_mult(splat, _scale_mult)
        _need_depth_overlay = (
            win._depth_occlusion
            and (win._show_bbox or win._show_grid)
        )
        _need_depth = _need_depth_overlay or DOF_ENABLED
        if _need_depth:
            arr, depth = render_frame_with_depth(
                splat, win._viewmat, win._K,
                win._w, win._h, colors=colors,
                camera_model=cam_model,
            )
            win._widget.set_depth_buffer(
                depth if _need_depth_overlay else None
            )
        elif SSAA_SCALE > 1:
            arr = render_frame_ssaa(
                splat, win._viewmat, win._K,
                win._w, win._h, SSAA_SCALE, colors,
                camera_model=cam_model,
            )
            win._widget.set_depth_buffer(None)
        else:
            rgb_t = render_frame_gpu(
                splat, win._viewmat, win._K,
                win._w, win._h, colors=colors,
                camera_model=cam_model,
            )
            win._widget.set_depth_buffer(None)
            _t_raster = _sync_ts(_dbg and _GPU_PROFILE)
    now = time.perf_counter()
    if win._last_ts > 0:
        _dt = now - win._last_ts
        instant = 1.0 / _dt
        win._fps = (
            instant if win._fps == 0.0
            else FPS_ALPHA * instant + (1 - FPS_ALPHA) * win._fps
        )

        fps_tick(win, _dt * 1000.0)
    win._last_ts = now
    if rgb_t is not None:

        if EXPOSURE != 1.0:
            rgb_t = apply_exposure_t(rgb_t, EXPOSURE)
        if SHARPEN_ENABLED:
            rgb_t = apply_sharpen_t(
                rgb_t, SHARPEN_AMOUNT, SHARPEN_RADIUS
            )
        if BLOOM_ENABLED:
            rgb_t = apply_bloom_t(
                rgb_t, BLOOM_THRESHOLD, BLOOM_INTENSITY, BLOOM_RADIUS,
            )
        if TOON_ENABLED:
            rgb_t = apply_toon_t(rgb_t, TOON_STEPS)
        _t_post = _sync_ts(_dbg and _GPU_PROFILE)
        arr = tensor_to_uint8(rgb_t)
        if _dbg and _GPU_PROFILE:
            _t_read = time.perf_counter()
    else:

        if EXPOSURE != 1.0:
            arr = (arr.astype(np.float32) * EXPOSURE).clip(
                0, 255
            ).astype(np.uint8)
        if DOF_ENABLED and depth is not None:
            arr = apply_dof(
                arr, depth,
                DOF_FOCUS_DIST, DOF_APERTURE, DOF_MAX_BLUR,
            )
        if SHARPEN_ENABLED:
            arr = apply_sharpen(arr, SHARPEN_AMOUNT, SHARPEN_RADIUS)
        if BLOOM_ENABLED:
            arr = apply_bloom(
                arr, BLOOM_THRESHOLD, BLOOM_INTENSITY, BLOOM_RADIUS,
            )
        if TOON_ENABLED:
            arr = apply_toon(arr, TOON_STEPS)
    win._widget.set_image(arr)
    _t_render = time.perf_counter()
    if win._seq_player is not None:

        tick = win._save_count if win._save_dir is not None else win._anim_tick
        seq_i = seq_overlay_index(
            PRESERVE_SEQUENCE_OVERLAY_DURATION, win._seq_idx, tick,
            win._seq_player.total_frames,
        )
        win._widget.set_seq_frame(
            win._seq_player.get_cached_frame(seq_i),
            win._seq_player.opacity,
        )
    else:
        win._widget.set_seq_frame(None, 0.0)
    win._widget.set_waveform_source(getattr(win, '_audio_source', None))
    is_ortho = cam_model == 'ortho'
    bbox, grid = compute_bbox_grid(
        win._splat, win._viewmat, win._K, ortho=is_ortho,
        want_bbox=win._show_bbox, want_grid=win._show_grid,
    )
    win._widget.set_bbox_lines(bbox)
    win._widget.set_grid(grid)

    _giz_w = win._widget.width() or win._w
    _giz_h = win._widget.height() or win._h
    win._widget.set_gizmo_overlay(
        compute_gizmo_axes(win._viewmat, _giz_h, _giz_w)
    )
    _update_overlay_channels(win, cam_model, is_ortho)

    win._cam_dirty = False
    if _dbg:
        _t_end = time.perf_counter()
        _proc_ms = (_t_proc - _t_start) * 1000.0
        _gpu_ms = (_t_render - _t_proc) * 1000.0
        _tail_ms = (_t_end - _t_render) * 1000.0
        _total_ms = (_t_end - _t_start) * 1000.0
        logger.debug(
            'PERF render_impl: proc %.2fms gpu %.2fms tail %.2fms '
            'total %.2fms', _proc_ms, _gpu_ms, _tail_ms, _total_ms,
        )
        perf_push(win, proc=_proc_ms, gpu=_gpu_ms, tail=_tail_ms,
                  total=_total_ms)

        if _t_read > 0.0:
            perf_push(
                win,
                raster=(_t_raster - _t_proc) * 1000.0,
                postfx=(_t_post - _t_raster) * 1000.0,
                readback=(_t_read - _t_post) * 1000.0,
            )
