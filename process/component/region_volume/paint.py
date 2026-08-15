from dataclasses import dataclass
import logging

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from configs.settings_transform import (
    TRANSFORM_HEAD_HEIGHT_RATIO, TRANSFORM_HEAD_WIDTH_RATIO)
from process.common.axis_arrow import filled_arrowhead_poly
from process.widget.scale import scaled_axis_cone_size
from process.component.region_volume.picking import project_point
from process.component.region_volume.settings import (
    REGION_VOLUME_AXIS_COLOR_X, REGION_VOLUME_AXIS_COLOR_Y, REGION_VOLUME_AXIS_COLOR_Z,
    REGION_VOLUME_HOVER_COLOR,
    REGION_VOLUME_LINE_WIDTH, REGION_VOLUME_HOVER_LINE_WIDTH,
)

logger = logging.getLogger(__name__)

def _hex_to_rgbf(h: str) -> tuple[float, float, float]:
    h = h.lstrip('#')
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )

@dataclass
class RegionVolumePalette:
    axis_colors: tuple[str, str, str] = (
        REGION_VOLUME_AXIS_COLOR_X, REGION_VOLUME_AXIS_COLOR_Y, REGION_VOLUME_AXIS_COLOR_Z,
    )
    hover_color: str = REGION_VOLUME_HOVER_COLOR
    line_width: int = REGION_VOLUME_LINE_WIDTH
    hover_line_width: int = REGION_VOLUME_HOVER_LINE_WIDTH

_DEFAULT_PALETTE: RegionVolumePalette = RegionVolumePalette()

def _axis_color(palette: RegionVolumePalette, axis: int, hovered: bool) -> QColor:
    if hovered:
        return QColor.fromRgbF(*_hex_to_rgbf(palette.hover_color))
    return QColor.fromRgbF(*_hex_to_rgbf(palette.axis_colors[axis]))

def _draw_axis_arrow(
    painter: QPainter,
    ox: int, oy: int, tx: int, ty: int,
    color: QColor, width: int, head_len: float, head_half: float,
) -> None:

    bx, by, head = filled_arrowhead_poly(
        ox, oy, tx, ty, head_len, head_half,
    )
    painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap))
    painter.drawLine(ox, oy, bx, by)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(color))
    painter.drawPolygon(head)

def paint_translate_region_volume(
    painter: QPainter, win,
    anchor: np.ndarray, axes: np.ndarray, world_len: float,
    hover_axis: int | None,
    palette: RegionVolumePalette | None = None,
    w: int = 0,
) -> None:
    p = palette or _DEFAULT_PALETTE

    cone = scaled_axis_cone_size(w)
    head_len = cone * TRANSFORM_HEAD_HEIGHT_RATIO
    head_half = cone * TRANSFORM_HEAD_WIDTH_RATIO
    a = anchor.astype(np.float32)
    origin_scr = project_point(win, a)
    if origin_scr is None:
        return
    ox, oy, _ = origin_scr
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for axis in range(3):
        tip = a + axes[axis].astype(np.float32) * world_len
        tip_scr = project_point(win, tip)
        if tip_scr is None:
            continue
        tx, ty, _ = tip_scr
        is_hover = hover_axis == axis
        color = _axis_color(p, axis, is_hover)
        width = p.hover_line_width if is_hover else p.line_width
        _draw_axis_arrow(
            painter, ox, oy, tx, ty, color, width, head_len, head_half)
    painter.restore()
