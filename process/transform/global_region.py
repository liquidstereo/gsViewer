import numpy as np

from process.transform.object_keyframe import _reorthogonalize

def lerp_transform_dict(src: dict, dst: dict, t: float) -> dict:
    inv = 1.0 - t
    out: dict = {}
    for key, d in dst.items():
        s = src.get(key)
        if s is None:
            out[key] = d
            continue
        R = s['rotation'] * inv + d['rotation'] * t
        out[key] = {
            'center':   (s['center'] * inv + d['center'] * t).astype(
                np.float32),
            'size':     (s['size'] * inv + d['size'] * t).astype(
                np.float32),
            'rotation': _reorthogonalize(R),
        }
    return out

def _members(window) -> list:
    reg = getattr(window, '_region_volume_registry', None)
    if reg is None:
        return []
    return list(getattr(reg, 'members', []))

def capture(window) -> dict:
    out: dict = {}
    for member in _members(window):
        target = getattr(member, 'target', None)
        label = getattr(member, 'overlay_label', '') or ''
        if target is None or not label:
            continue
        out[label] = {
            'center':   np.asarray(target.center, np.float32).copy(),
            'size':     np.asarray(target.size, np.float32).copy(),
            'rotation': np.asarray(target.rotation, np.float32).copy(),
        }
    return out

def apply(window, regions: dict) -> None:
    if not regions:
        return
    by_label = {
        (getattr(m, 'overlay_label', '') or ''): m
        for m in _members(window)
    }
    for label, state in regions.items():
        member = by_label.get(label)
        target = getattr(member, 'target', None) if member else None
        if target is None:
            continue
        target.center = state['center']
        target.size = state['size']
        target.rotation = state['rotation']
