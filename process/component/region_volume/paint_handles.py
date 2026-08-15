import logging

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from process.component.region_volume.paint import (
    RegionVolumePalette, _DEFAULT_PALETTE, _axis_color, _hex_to_rgbf,
)
from process.component.region_volume.picking import _view_mats, project_point
from process.component.region_volume.settings import (
    REGION_VOLUME_HANDLE_BRUSH_ALPHA, REGION_VOLUME_HANDLE_HOVER_BORDER_PX,
    REGION_VOLUME_HANDLE_PEN_ALPHA,
    REGION_VOLUME_SCALE_CENTER_BOX_PX, REGION_VOLUME_SCALE_HANDLE_SIZE_PX,
)

logger = logging.getLogger(__name__)

_SCALE_HANDLE_SIZE_PX: int = REGION_VOLUME_SCALE_HANDLE_SIZE_PX
_SCALE_CENTER_BOX_PX: int = REGION_VOLUME_SCALE_CENTER_BOX_PX
_ROTATE_RING_SAMPLES: int = 48

def paint_scale_region_volume(
    painter: QPainter, win,
    anchor: np.ndarray, axes: np.ndarray, world_len: float,
    hover_axis: int | None,
    palette: RegionVolumePalette | None = None,
) -> None:
    p = palette or _DEFAULT_PALETTE
    a = anchor.astype(np.float32)
    origin_scr = project_point(win, a)
    if origin_scr is None:
        return
    ox, oy, _ = origin_scr
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    for axis in range(3):
        tip = a + axes[axis].astype(np.float32) * world_len
        tip_scr = project_point(win, tip)
        if tip_scr is None:
            continue
        tx, ty, _ = tip_scr
        is_hover = hover_axis == axis
        color = _axis_color(p, axis, is_hover)
        width = p.hover_line_width if is_hover else p.line_width
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(ox, oy, tx, ty)
        painter.setBrush(QBrush(color))
        h = _SCALE_HANDLE_SIZE_PX // 2
        painter.drawRect(tx - h, ty - h, h * 2, h * 2)
    painter.restore()

def paint_region_volume_shift_indicator(
    painter: QPainter, win, anchor: np.ndarray,
    palette: RegionVolumePalette | None = None,
) -> None:
    p = palette or _DEFAULT_PALETTE
    scr = project_point(win, anchor.astype(np.float32))
    if scr is None:
        return
    ox, oy, _ = scr
    hov = QColor.fromRgbF(*_hex_to_rgbf(p.hover_color))
    pen_col = QColor(hov.red(), hov.green(), hov.blue(),
                     REGION_VOLUME_HANDLE_PEN_ALPHA)
    brush_col = QColor(hov.red(), hov.green(), hov.blue(),
                       REGION_VOLUME_HANDLE_BRUSH_ALPHA)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(pen_col, REGION_VOLUME_HANDLE_HOVER_BORDER_PX))
    painter.setBrush(QBrush(brush_col))
    h = _SCALE_CENTER_BOX_PX // 2
    painter.drawRect(ox - h, oy - h, h * 2, h * 2)
    painter.restore()

def _project_circle(
    win, center: np.ndarray, u: np.ndarray, v: np.ndarray,
    radius: float, samples: int,
) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for i in range(samples + 1):
        ang = 2.0 * np.pi * (i / samples)
        offset = (
            u * float(np.cos(ang)) + v * float(np.sin(ang))
        ) * radius
        p = center + offset
        scr = project_point(win, p.astype(np.float32))
        if scr is None:
            continue
        out.append((scr[0], scr[1]))
    return out

def paint_rotate_region_volume(
    painter: QPainter, win,
    anchor: np.ndarray, axes: np.ndarray, world_len: float,
    hover_axis: int | None,
    palette: RegionVolumePalette | None = None,
) -> None:
    p = palette or _DEFAULT_PALETTE
    if _view_mats(win) is None:
        return
    a = anchor.astype(np.float32)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for axis in range(3):
        u = axes[(axis + 1) % 3].astype(np.float32)
        v = axes[(axis + 2) % 3].astype(np.float32)
        pts = _project_circle(
            win, a, u, v, world_len, _ROTATE_RING_SAMPLES,
        )
        if len(pts) < 2:
            continue
        is_hover = hover_axis == axis
        color = _axis_color(p, axis, is_hover)
        width = p.hover_line_width if is_hover else p.line_width
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            painter.drawLine(x1, y1, x2, y2)
    painter.restore()
