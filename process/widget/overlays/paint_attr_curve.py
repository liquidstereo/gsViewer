from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter

from configs.settings_attr import (
    ATTR_PANEL_CURVE_HANDLE_R_RATIO, ATTR_PANEL_CURVE_PAD_RATIO,
    ATTR_PANEL_CURVE_ROWS, ATTR_PANEL_FILL_COLOR, ATTR_PANEL_HANDLE_COLOR,
    ATTR_PANEL_LABEL_COLOR, ATTR_PANEL_TRACK_COLOR,
)
from configs.settings_color import ATTR_PANEL_HOVER_COLOR
from process.widget.overlays.attr_spec import AttrRow
from process.widget.overlays.curve_model import points_to_lut
from process.widget.qt_paint import qcolor_from_hex
from process.widget.text_case import apply_overlay_case

_LUT_N = 96

def paint_curve(painter: QPainter, fm, sp, tx: float, baseline: float,
                m: dict, collapsed: bool) -> list:
    content_w = m['panel_w'] - m['pad'] * 2
    hdr = AttrRow(
        sp, tx, baseline - m['ascent'], content_w, m['line_h'],
        role='curve_header')
    mouse = m.get('mouse')
    hover = mouse is not None and hdr.hit(mouse[0], mouse[1])
    marker = '+ ' if collapsed else '- '
    painter.setPen(qcolor_from_hex(
        ATTR_PANEL_HOVER_COLOR if hover else ATTR_PANEL_LABEL_COLOR))
    painter.drawText(
        int(tx), int(baseline), apply_overlay_case(marker + sp.label))
    rows = [hdr]
    if collapsed:
        return rows

    box_baseline = baseline + m['line_h'] + m['sep_gap']
    box_y = box_baseline - m['ascent']
    box_h = (m['line_h'] * ATTR_PANEL_CURVE_ROWS
             - m['line_h'] * ATTR_PANEL_CURVE_PAD_RATIO)
    _paint_box(painter, fm, sp, tx, box_y, content_w, box_h)
    rows.append(AttrRow(sp, tx, box_y, content_w, box_h, role='curve_box'))
    return rows

def _paint_box(painter: QPainter, fm, sp, box_x: float, box_y: float,
               box_w: float, box_h: float) -> None:
    painter.setPen(qcolor_from_hex(ATTR_PANEL_TRACK_COLOR))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(QRectF(box_x, box_y, box_w, box_h))
    pts = list(sp.get() or [])
    lut = points_to_lut(pts, _LUT_N)
    painter.setPen(qcolor_from_hex(ATTR_PANEL_FILL_COLOR))
    prev = None
    for i in range(_LUT_N):
        px = box_x + (i / (_LUT_N - 1)) * box_w
        py = box_y + (1.0 - float(lut[i])) * box_h
        if prev is not None:
            painter.drawLine(int(prev[0]), int(prev[1]), int(px), int(py))
        prev = (px, py)
    hr = max(3.0, fm.height() * ATTR_PANEL_CURVE_HANDLE_R_RATIO)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(qcolor_from_hex(ATTR_PANEL_HANDLE_COLOR))
    for p in pts:
        cx = min(1.0, max(0.0, float(p[0])))
        cy = min(1.0, max(0.0, float(p[1])))
        px = box_x + cx * box_w
        py = box_y + (1.0 - cy) * box_h
        painter.drawEllipse(QRectF(px - hr, py - hr, hr * 2, hr * 2))
