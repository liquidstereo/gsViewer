import math

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (
    QBrush, QFontMetrics, QPainter, QPen, QPolygon)

from process.common.font import make_font
from configs.settings_color import GIZMO_INDICATOR_DOT_COLOR
from process.widget.qt_paint import qcolor_from_hex
from process.widget.scale import (
    scaled_axis_arrow_width, scaled_axis_cone_size, scaled_axis_label_gap,
    scaled_axis_label_size,
)

_DEPTH_LABEL_DIR: tuple[float, float] = (0.7071, 0.7071)

def _draw_arrowhead(
    painter: QPainter,
    x1: int, y1: int, x2: int, y2: int, size: int,
) -> None:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    half = size * 0.45
    bx = x2 - int(ux * size)
    by = y2 - int(uy * size)
    v1 = QPoint(int(bx - uy * half), int(by + ux * half))
    v2 = QPoint(int(bx + uy * half), int(by - ux * half))
    painter.drawPolygon(QPolygon([QPoint(x2, y2), v1, v2]))

def axis_label_pos(
    cx: int, cy: int, x2: int, y2: int, gap: int,
) -> tuple[int, int]:
    dx, dy = float(x2 - cx), float(y2 - cy)
    length = math.hypot(dx, dy)
    if length < float(gap):
        ux, uy = _DEPTH_LABEL_DIR
    else:
        ux, uy = dx / length, dy / length
    return int(round(x2 + ux * gap)), int(round(y2 + uy * gap))

def paint_gizmo_overlay(
    painter: QPainter,
    axis_indicator: list,
    w: int,
    y_offset: int = 0,
) -> None:
    painter.save()
    if y_offset:
        painter.translate(0, -int(y_offset))
    cx, cy, _, _, _, _ = axis_indicator[0]
    arrow_w = scaled_axis_arrow_width(w)
    cone_size = scaled_axis_cone_size(w)
    dot_r = max(2, round(3 * (arrow_w / 3.0)))
    painter.setBrush(QBrush(qcolor_from_hex(GIZMO_INDICATOR_DOT_COLOR)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QPoint(cx, cy), dot_r, dot_r)
    lbl_f = make_font()
    lbl_f.setPointSize(scaled_axis_label_size(w))
    lbl_f.setBold(True)
    fm = QFontMetrics(lbl_f)
    gap = scaled_axis_label_gap(w)
    for x1, y1, x2, y2, color, label in axis_indicator:
        c = qcolor_from_hex(color)
        sx = x1 + int((x2 - x1) * 0.65)
        sy = y1 + int((y2 - y1) * 0.65)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(c, arrow_w))
        painter.drawLine(x1, y1, sx, sy)
        painter.setBrush(QBrush(c))
        painter.setPen(Qt.PenStyle.NoPen)
        _draw_arrowhead(painter, sx, sy, x2, y2, cone_size)
        painter.setFont(lbl_f)
        painter.setPen(c)
        lx, ly = axis_label_pos(x1, y1, x2, y2, gap)
        painter.drawText(
            lx - fm.horizontalAdvance(label) // 2,
            ly + (fm.ascent() - fm.descent()) // 2, label)
    painter.restore()
