from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter

from configs.settings_attr import (
    ATTR_PANEL_DROPDOWN_MARK, ATTR_PANEL_FILL_COLOR, ATTR_PANEL_HANDLE_COLOR,
    ATTR_PANEL_HANDLE_R_RATIO, ATTR_PANEL_TRACK_COLOR,
    ATTR_PANEL_TRACK_H_RATIO, ATTR_PANEL_VALUE_COLOR,
)
from configs.settings_color import ATTR_PANEL_HOVER_COLOR
from process.widget.overlays.attr_spec import (
    AttrRow, KIND_BOOL, KIND_BUTTON, KIND_ENUM, KIND_LABEL, KIND_METER,
)
from process.widget.overlays.paint_attr_button import paint_button
from process.widget.qt_paint import qcolor_from_hex
from process.widget.text_case import apply_overlay_case

def _over(m: dict, x: float, y: float, w: float, h: float) -> bool:
    mouse = m.get('mouse')
    if mouse is None:
        return False
    return x <= mouse[0] <= x + w and y <= mouse[1] <= y + h

def _value_color(m: dict, x: float, y: float, w: float, h: float,
                 default: str) -> str:
    return ATTR_PANEL_HOVER_COLOR if _over(m, x, y, w, h) else default

def paint_control(painter: QPainter, fm, sp, tx: float, baseline: float,
                  m: dict) -> AttrRow | None:
    ctrl_x = tx + m['label_w'] + m['gap']
    right = m['x0'] + m['panel_w'] - m['pad']
    if sp.kind == KIND_BUTTON:
        return paint_button(painter, fm, sp, tx, baseline, right, m)
    if sp.kind == KIND_BOOL:
        return _paint_checkbox(painter, fm, sp, baseline, right, m)
    if sp.kind == KIND_ENUM:
        return _paint_enum(painter, fm, sp, baseline, right, m)
    if sp.kind == KIND_LABEL:
        return _paint_readout(painter, fm, sp, baseline, right)
    if sp.kind == KIND_METER:
        return _paint_meter(painter, fm, sp, ctrl_x, baseline, right, m)
    return _paint_slider(painter, fm, sp, ctrl_x, baseline, right, m)

def _paint_readout(painter: QPainter, fm, sp, baseline: float,
                   right: float) -> None:
    vt = apply_overlay_case(sp.value_text())
    vx = right - fm.horizontalAdvance(vt)
    painter.setPen(qcolor_from_hex(ATTR_PANEL_VALUE_COLOR))
    painter.drawText(int(vx), int(baseline), vt)
    return None

def _paint_meter(painter: QPainter, fm, sp, ctrl_x: float, baseline: float,
                 right: float, m: dict) -> None:

    vt = apply_overlay_case(sp.value_text())
    vx = right - fm.horizontalAdvance(vt)
    painter.setPen(qcolor_from_hex(ATTR_PANEL_VALUE_COLOR))
    painter.drawText(int(vx), int(baseline), vt)
    track_w = m['slider_w']

    track_h = max(2, int(round(fm.height() * ATTR_PANEL_TRACK_H_RATIO)))
    track_y = int(round(baseline - fm.ascent() * 0.45 - track_h * 0.5))
    ratio = sp.norm()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(qcolor_from_hex(ATTR_PANEL_FILL_COLOR))
    painter.drawRect(QRectF(
        int(ctrl_x), track_y, int(track_w * ratio), track_h))
    return None

def _paint_checkbox(painter: QPainter, fm, sp, baseline: float,
                    right: float, m: dict) -> AttrRow:
    box = fm.ascent()
    bx = right - box
    top = baseline - fm.ascent()
    edge = _value_color(m, bx, top, box, box, ATTR_PANEL_HANDLE_COLOR)
    painter.setPen(qcolor_from_hex(edge))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(QRectF(bx, top, box, box))
    if sp.get is not None and sp.get():
        inset = box * 0.25
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor_from_hex(ATTR_PANEL_FILL_COLOR))
        painter.drawRect(QRectF(
            bx + inset, top + inset, box - inset * 2, box - inset * 2))
    return AttrRow(sp, bx, top, box, box)

def _paint_enum(painter: QPainter, fm, sp, baseline: float,
                right: float, m: dict) -> AttrRow:
    vt = apply_overlay_case(sp.value_text() + ATTR_PANEL_DROPDOWN_MARK)
    vw = fm.horizontalAdvance(vt)
    vx = right - vw
    top = baseline - fm.ascent()
    color = _value_color(m, vx, top, vw, fm.height(), ATTR_PANEL_HANDLE_COLOR)
    painter.setPen(qcolor_from_hex(color))
    painter.drawText(int(vx), int(baseline), vt)
    return AttrRow(sp, vx, top, vw, fm.height())

def _paint_slider(painter: QPainter, fm, sp, ctrl_x: float, baseline: float,
                  right: float, m: dict) -> AttrRow:
    top = baseline - fm.ascent()
    track_w = m['slider_w']

    hov = _over(m, ctrl_x, top, track_w, fm.height())
    vt = apply_overlay_case(sp.value_text())
    vw = fm.horizontalAdvance(vt)
    value_x = right - vw
    val_c = ATTR_PANEL_HOVER_COLOR if hov else ATTR_PANEL_VALUE_COLOR
    painter.setPen(qcolor_from_hex(val_c))
    painter.drawText(int(value_x), int(baseline), vt)
    track_h = max(2.0, fm.height() * ATTR_PANEL_TRACK_H_RATIO)
    track_y = baseline - fm.ascent() * 0.45 - track_h * 0.5
    ratio = sp.norm()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(qcolor_from_hex(ATTR_PANEL_TRACK_COLOR))
    painter.drawRoundedRect(
        QRectF(ctrl_x, track_y, track_w, track_h), track_h * 0.5,
        track_h * 0.5)
    painter.setBrush(qcolor_from_hex(ATTR_PANEL_FILL_COLOR))
    painter.drawRoundedRect(
        QRectF(ctrl_x, track_y, track_w * ratio, track_h), track_h * 0.5,
        track_h * 0.5)
    hr = max(3.0, fm.height() * ATTR_PANEL_HANDLE_R_RATIO)
    hx = ctrl_x + track_w * ratio
    hy = track_y + track_h * 0.5
    hnd_c = ATTR_PANEL_HOVER_COLOR if hov else ATTR_PANEL_HANDLE_COLOR
    painter.setBrush(qcolor_from_hex(hnd_c))
    painter.drawEllipse(QRectF(hx - hr, hy - hr, hr * 2, hr * 2))
    return AttrRow(sp, ctrl_x, top, track_w, fm.height())
