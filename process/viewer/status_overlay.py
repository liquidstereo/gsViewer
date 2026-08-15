import numpy as np

from configs.settings_overlay import DISPLAY_STATUS_LOCK, DISPLAY_STATUS_SOLO
from process.common import display_name
from process.overlay_coord_io import (
    to_display_center, to_display_euler, to_display_scale)
from process.common.timefmt import fmt_mmss_ms as _fmt_ms
from process.data.loader import get_slice_ratio
from process.widget.text_case import keep_case

_IDENTITY: np.ndarray = np.eye(3, dtype=np.float32)

def _display_yup_position(data_pos: np.ndarray) -> tuple[float, float, float]:
    p = to_display_center(data_pos)
    return float(p[0]), float(p[1]), float(p[2])

def _display_size_ratio(
    size: np.ndarray, base_size: np.ndarray,
) -> tuple[float, float, float]:
    r = to_display_scale(size, base_size)
    return float(r[0]), float(r[1]), float(r[2])

def _display_yup_rotation_euler(
    rotation: np.ndarray, base_rotation: np.ndarray,
) -> tuple[float, float, float]:
    e = to_display_euler(rotation, base_rotation)
    return float(e[0]), float(e[1]), float(e[2])

def _object_data(win, controller, input_id: str) -> dict | None:
    target = controller.targets.get(input_id)
    if target is None:
        return None
    return {
        'label': keep_case(display_name(win, input_id)),
        'center': target.center,
        'size': target.size,
        'base_size': target.initial_size,
        'rotation': target.rotation,
        'base_rotation': _IDENTITY,
        'count': int(getattr(target, 'point_count', 0)),
        'lock': controller.is_locked(input_id),
        'solo': bool(controller.solo_id == input_id),
    }

def _active_provider_data(win) -> dict | None:
    for provider in getattr(win, '_status_providers', ()) or ():
        try:
            data = provider()
        except Exception:
            data = None
        if data is not None:
            return data
    return None

def _default_object_data(win, controller) -> dict | None:
    targets = controller.targets
    if not targets:
        return None
    if '__primary__' in targets:
        key = '__primary__'
    else:
        active = getattr(win, '_active_id', None)
        key = active if active in targets else next(iter(targets))
    return _object_data(win, controller, key)

def _format_objinfo(data: dict) -> str:
    count = data.get('count')
    label = data.get('label', '')
    if count is None:
        return f'{label}'
    return f'{label} . POINTS: {count:,}'

def _channel_name(ch: int) -> str:

    if ch <= 0:
        return ''
    if ch == 1:
        return 'Mono'
    if ch == 2:
        return 'Stereo'
    return f'{ch}ch'

def _format_audio_format(data: dict) -> str:

    parts: list[str] = []
    sr = int(data.get('sr', 0))
    if sr > 0:
        parts.append(f'{sr} Hz')
    bits = int(data.get('bits', 0))
    if bits > 0:
        parts.append(f'{bits}-bit')
    ch_name = _channel_name(int(data.get('channels', 0)))
    if ch_name:
        parts.append(ch_name)
    if not parts:
        return ''

    return '. '.join(parts)

def _format_audio_block(data: dict) -> str:

    pos = _fmt_ms(float(data.get('pos', 0.0)))
    dur = _fmt_ms(float(data.get('duration', 0.0)))
    time_line = f'{pos}' if data.get('brief') else f'{pos} / {dur}'
    lines = [f'[TITLE]{data.get("label", "")}', time_line]
    fmt = _format_audio_format(data)
    if fmt:
        lines.append(fmt)
    return '\n'.join(lines)

def _format_lines_block(data: dict) -> str:

    lines = []
    label = data.get('label', '')
    if label:
        lines.append(f'[TITLE]{label}')
    lines.extend(str(line) for line in data.get('lines', ()))
    return '\n'.join(lines)

def _format_status_block(data: dict) -> str:
    if data.get('kind') == 'audio':
        return _format_audio_block(data)
    if 'lines' in data:
        return _format_lines_block(data)
    cx, cy, cz = _display_yup_position(data['center'])
    sx, sy, sz = _display_size_ratio(data['size'], data['base_size'])
    rx, ry, rz = _display_yup_rotation_euler(
        data['rotation'], data['base_rotation'],
    )
    lock = data.get('lock')
    label = data.get('label', '')
    count = data.get('count')
    if count is None:
        title_text = label
    else:
        title_text = f'{label} . POINTS: {count:,}'
    solo = data.get('solo')
    lines = [
        f'[TITLE]{title_text}',
        f'POSITION. X: {cx:.3f} . Y: {cy:.3f} . Z: {cz:.3f}',
        f'SCALE. X: {sx:.3f} . Y: {sy:.3f} . Z: {sz:.3f}',
        f'ROTATE. X: {rx:.3f} . Y: {ry:.3f} . Z: {rz:.3f}',
    ]
    if DISPLAY_STATUS_LOCK:
        lock_state = 'None' if lock is None else ('ON' if lock else 'OFF')
        lines.append(f'LOCK. {lock_state}')
    if DISPLAY_STATUS_SOLO:
        solo_state = 'None' if solo is None else ('ON' if solo else 'OFF')
        lines.append(f'SOLO. {solo_state}')
    _append_slice_ratio(lines, count)
    return '\n'.join(lines)

def _append_slice_ratio(lines: list, count: int | None) -> None:

    ratio = get_slice_ratio()
    if ratio >= 1.0:
        return
    pct = round(ratio * 100)
    if count and ratio > 0.0:
        stride = max(1, round(1.0 / ratio))
        full = count * stride
        lines.append(
            f'SLICE RATIO. {pct}% ({full:,} -> {count:,})'
        )
    else:
        lines.append(f'SLICE RATIO. {pct}%')

def _playing_object_data(win, controller) -> dict | None:
    if controller is None:
        return None
    active = getattr(win, '_chain_active_iid', None)
    if active is None and getattr(win, '_scheduler', None) is not None:
        active = getattr(win, '_active_id', None)
    if active is None:
        return None
    data = _object_data(win, controller, active)
    if data is not None:
        return data
    default = _default_object_data(win, controller)
    if default is not None:
        default = dict(default)
        default['label'] = keep_case(display_name(win, active))
    return default

def _selected_data(win) -> dict | None:
    controller = getattr(win, '_input_transform', None)
    if controller is not None and controller.selected_id is not None:
        data = _object_data(win, controller, controller.selected_id)
        if data is not None:
            return data
    region = _active_provider_data(win)
    if region is not None:
        return region
    return _playing_object_data(win, controller)

def build_objinfo_overlay(win) -> str:
    controller = getattr(win, '_input_transform', None)
    if controller is not None:
        default = _default_object_data(win, controller)
        if default is not None:
            return _format_objinfo(default)
    return ''

def build_status_overlay(win) -> str:
    data = _selected_data(win)
    if data is None:
        return ''
    return _format_status_block(data)
