import time

import torch

from configs.settings_overlay import (
    DISPLAY_INFO_INPUT_PATH, INPUT_PATH_MAX_CHARS, COMMENT_OVERLAY_TEXT,
    BUFFER_MESSAGE,
)
from configs.settings_color import (
    MODE_ANISO_CMAP, MODE_ACCUM_CMAP, MODE_SCALE_CMAP, MODE_SH_CMAP,
    MODE_MEDIAN_DEPTH_CMAP, MODE_HIT_COUNT_CMAP,
)
from process.annotation.markers import compute_annotation_markers
from process.handle import get_last_alert, get_recent_logs
from process.mode import RenderMode
from process.overlay_coord import display_eye_yup_from_viewmat
from process.transform.global_keyframe import compute_global_object_markers
from process.transform.object_keyframe import (
    compute_selected_object_markers,
)
from process.viewer.status_overlay import (
    build_objinfo_overlay, build_status_overlay,
)
from process.widget.text_case import keep_case

_WHITE: tuple[float, float, float] = (1.0, 1.0, 1.0)

def _apply_scale_mult(splat: dict, mult: float) -> dict:
    if mult == 1.0:
        return splat
    out = dict(splat)
    out['scales'] = splat['scales'] * mult
    return out

def _abbrev_path(path_str: str, limit: int = INPUT_PATH_MAX_CHARS) -> str:
    if len(path_str) < limit:
        return path_str
    parts = path_str.replace('\\', '/').rstrip('/').split('/')
    if len(parts) < 2:
        return path_str
    return f'.../{parts[-2]}/{parts[-1]}'

def _input_frame_path(win, input_id: str) -> str:
    files = win._inputs[input_id]['files']
    local = win._idx % max(1, len(files))
    return str(files[local])

def _compose_input_label(win, multi: bool) -> str:
    if not multi:
        return _abbrev_path(str(win._files[win._local_idx]))
    itc = getattr(win, '_input_transform', None)
    sel = getattr(itc, 'selected_id', None) if itc is not None else None
    if sel is not None and sel in win._inputs:
        return _abbrev_path(_input_frame_path(win, sel))
    ids = win.input_ids()
    base = _abbrev_path(_input_frame_path(win, ids[0]))
    extra = len(ids) - 1
    return f'{base} (+{extra} more)' if extra > 0 else base

_CMAP_BAR: dict = {
    RenderMode.ANISO:        (MODE_ANISO_CMAP,        'Aniso',  'Iso',    None),
    RenderMode.ACCUMULATION: (MODE_ACCUM_CMAP,         '1.0',    '0.0',   _WHITE),
    RenderMode.SCALE:        (MODE_SCALE_CMAP,         'Large',  'Small',  None),
    RenderMode.SH:           (MODE_SH_CMAP,            'High',   'Low',    None),
    RenderMode.HIT_COUNT:    (MODE_HIT_COUNT_CMAP,     'Max',    '0',     _WHITE),
    RenderMode.MEDIAN_DEPTH: (MODE_MEDIAN_DEPTH_CMAP,  'Far',    'Near',   None),
    RenderMode.OPACITY:      ('gray',                  '1.0',    '0.0',    None),
}

def _get_cmap_bar_info(mode: RenderMode) -> dict | None:
    entry = _CMAP_BAR.get(mode)
    if entry is None:
        return None
    cmap, label_top, label_bot, text_clr = entry
    return {
        'cmap': cmap, 'label_top': label_top,
        'label_bot': label_bot, 'text_clr': text_clr,
    }

def _sys_overlay(s: dict | None, g: dict | None) -> str:
    if not s:
        return 'LOADING SYSTEM STATS...'
    r = f'CPU {s["cpu_percent"]:.1f}% . MEM {s["memory_percent"]:.1f}%'
    if g:
        r += f' . GPU {g["gpu_percent"]:.1f}% . VRAM {g["vram_percent"]:.1f}%'
    return r

def _cam_overlay(viewmat, cam: dict, K, camera_model: str = 'pinhole') -> str:

    pos = display_eye_yup_from_viewmat(viewmat)

    zoom = float(cam.get('fx_scale', 1.0))
    prefix = 'ORTHO' if camera_model == 'ortho' else 'PERSP'
    return (
        f'{prefix}. CAM. X: {pos[0]:.3f} . Y: {pos[1]:.3f} . Z: {pos[2]:.3f}'
        f' . DOLLY: {cam["distance"]:.3f} . ZOOM: {zoom:.3f}'
    )

def _sync_ts(dbg: bool) -> float:

    if not dbg:
        return 0.0
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    return time.perf_counter()

def _update_overlay_channels(win, cam_model: str, is_ortho: bool) -> None:

    _li = win._local_idx
    _multi = len(win._inputs) > 1
    _total = getattr(win, '_total_frames', len(win._files))
    _master = win._idx if _multi else _li
    _denom = _total if _multi else len(win._files)
    win._widget.set_render_mode(win._render_mode)
    _input_path = _compose_input_label(win, _multi)

    if DISPLAY_INFO_INPUT_PATH :
        _info_text = (
            f'FPS: {win._fps:.1f}  |  '
            f'{_master + 1:04d}/{_denom:04d}  |  '
            f'INPUT: {keep_case(_input_path)}'
        )
    else :
        _info_text = (
            f'FPS: {win._fps:.1f}  |  '
            f'{_master + 1:04d}/{_denom:04d}'
        )
    if getattr(win, '_save_time_diff_msg', ''):
        _info_text = f'{_info_text}\n{win._save_time_diff_msg}'
    win._widget.set_info_overlay(_info_text)
    win._widget.set_stat_overlay(
        _sys_overlay(win._sys_info, win._gpu_info)
    )
    win._widget.set_cam_overlay(
        _cam_overlay(win._viewmat, win._cam, win._K, cam_model)
    )
    win._widget.set_objinfo_overlay(build_objinfo_overlay(win))
    if win._widget._compact_overlays:

        win._widget.set_status_overlay('')
        win._widget.set_object_list([])
        win._widget.set_audio_list([])
        win._widget.set_region_list([])
    else:
        win._widget.set_status_overlay(build_status_overlay(win))

        for _attr, _setter in (
            ('_object_list_provider', win._widget.set_object_list),
            ('_audio_list_provider', win._widget.set_audio_list),
            ('_region_list_provider', win._widget.set_region_list),
        ):
            _prov = getattr(win, _attr, None)
            _setter(_prov() if _prov is not None else [])
    _alert_seq, _alert_msg = get_last_alert()
    if _alert_seq != win._last_alert_seq:
        win._last_alert_seq = _alert_seq
        win._message_overlay = _alert_msg

        win._hover_overlay = ''
        win._message_overlay_timer.start()
    win._widget.set_message_overlay(
        getattr(win, '_hover_overlay', '') or win._message_overlay or None
    )
    win._widget.set_loading_overlay(
        getattr(win, '_buffer_message', BUFFER_MESSAGE)
        if getattr(win, '_buffering', False) else None
    )
    if win._show_logs:
        current = get_recent_logs()
        if current != win._last_log_snapshot:
            win._widget.set_log_overlay(current)
            win._last_log_snapshot = current
    else:
        win._widget.set_log_overlay([])
    win._widget.set_comment_overlay(COMMENT_OVERLAY_TEXT)

    win._widget.set_colormap_bar(
        _get_cmap_bar_info(win._render_mode)
        if win._show_colormap else None
    )
    if win._show_annot and win._annot.count() > 0:
        markers = compute_annotation_markers(
            win._annot.items(), win._viewmat, win._K, ortho=is_ortho,
        )
        win._widget.set_annotations(markers)
    else:
        win._widget.set_annotations([])
    win._widget.set_object_kf_markers(
        compute_selected_object_markers(
            win, win._viewmat, win._K, ortho=is_ortho,
        )
    )
    win._widget.set_global_kf_markers(
        compute_global_object_markers(
            win, win._viewmat, win._K, ortho=is_ortho,
        )
    )
