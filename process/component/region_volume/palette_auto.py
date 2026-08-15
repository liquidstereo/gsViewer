import colorsys
import random

from configs.settings_color import (
    DESELECTED_COLOR, REGION_PALETTE_SATURATION, SELECTED_COLOR)

_HUE_BASE: float = random.random()

_FORBIDDEN_MARGIN: float = 0.06

def _hex_to_hue(hex_color: str) -> float:
    h = hex_color.lstrip('#')
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return colorsys.rgb_to_hsv(r, g, b)[0]

def _build_allowed_segments() -> list[tuple[float, float]]:
    centers = [_hex_to_hue(SELECTED_COLOR), _hex_to_hue(DESELECTED_COLOR)]
    bands: list[tuple[float, float]] = []
    for c in centers:
        a = (c - _FORBIDDEN_MARGIN) % 1.0
        b = (c + _FORBIDDEN_MARGIN) % 1.0
        if a <= b:
            bands.append((a, b))
        else:
            bands.append((a, 1.0))
            bands.append((0.0, b))
    bands.sort()
    merged: list[tuple[float, float]] = []
    for a, b in bands:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    allowed: list[tuple[float, float]] = []
    prev = 0.0
    for a, b in merged:
        if a > prev:
            allowed.append((prev, a))
        prev = b
    if prev < 1.0:
        allowed.append((prev, 1.0))
    return allowed or [(0.0, 1.0)]

_ALLOWED_SEGMENTS: list[tuple[float, float]] = _build_allowed_segments()

def _map_to_allowed(t: float) -> float:
    total = sum(b - a for a, b in _ALLOWED_SEGMENTS)
    x = (t % 1.0) * total
    for a, b in _ALLOWED_SEGMENTS:
        seg = b - a
        if x < seg:
            return a + x
        x -= seg
    return _ALLOWED_SEGMENTS[-1][1]

def auto_hue_color(idx: int, total: int) -> str:
    t = (_HUE_BASE + idx / max(2, total)) % 1.0
    hue = _map_to_allowed(t)
    r, g, b = colorsys.hsv_to_rgb(hue, REGION_PALETTE_SATURATION, 1.0)
    return '#{:02x}{:02x}{:02x}'.format(
        int(r * 255), int(g * 255), int(b * 255),
    )
