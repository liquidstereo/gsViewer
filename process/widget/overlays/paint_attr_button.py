from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from configs.settings_attr import (
    ATTR_PANEL_BUTTON_BG, ATTR_PANEL_BUTTON_BORDER, ATTR_PANEL_BUTTON_H_SCALE,
    ATTR_PANEL_BUTTON_TEXT, ATTR_PANEL_CORNER_RADIUS,
)
from configs.settings_color import (
    ATTR_PANEL_BUTTON_CLICK_BG, ATTR_PANEL_BUTTON_HOVER_BG,
    ATTR_PANEL_HOVER_COLOR,
)
from process.widget.overlays.attr_spec import AttrRow, KIND_BUTTON
from process.widget.qt_paint import qcolor_from_hex
from process.widget.text_case import apply_overlay_case

def _btn_gap(fm) -> float:
    return fm.horizontalAdvance(' ') * 2

def _btn_intrinsic_w(fm, sp) -> float:
    text_w = fm.horizontalAdvance(apply_overlay_case(sp.label))
    return text_w + _btn_gap(fm) * 2

def button_run_count(specs: list) -> int:
    n = 0
    prev_btn = False
    for sp in specs:
        is_btn = sp.kind == KIND_BUTTON
        if is_btn and (not prev_btn or sp.row_break):
            n += 1
        prev_btn = is_btn
    return n

def button_row_width(fm, specs: list) -> float:
    gap = _btn_gap(fm)
    widest = 0.0
    run_max = 0.0
    run_n = 0
    for sp in specs:
        is_btn = sp.kind == KIND_BUTTON
        if (not is_btn or (sp.row_break and run_n)) and run_n:
            widest = max(widest, run_max * run_n + gap * (run_n - 1))
            run_max = 0.0
            run_n = 0
        if is_btn:
            run_max = max(run_max, _btn_intrinsic_w(fm, sp))
            run_n += 1
    if run_n:
        widest = max(widest, run_max * run_n + gap * (run_n - 1))
    return widest

def paint_button_row(painter: QPainter, fm, specs: list, baseline: float,
                     m: dict) -> list:
    gap = _btn_gap(fm)
    left = m['x0'] + m['pad']
    avail = m['panel_w'] - m['pad'] * 2
    n = len(specs)
    cell = (avail - gap * (n - 1)) / n if n else avail
    rows: list = []
    x = left
    for sp in specs:
        rows.append(paint_button(painter, fm, sp, x, baseline, x + cell, m))
        x += cell + gap
    return rows

def _button_over(bx: float, top: float, bw: float, bh: float,
                 m: dict) -> bool:
    mouse = m.get('mouse')
    return (
        mouse is not None
        and bx <= mouse[0] <= bx + bw and top <= mouse[1] <= top + bh
    )

def _button_bg(sp, bx: float, top: float, bw: float, bh: float,
               m: dict) -> str:
    over = _button_over(bx, top, bw, bh, m)
    if over and m.get('pressed') == sp.label:
        return ATTR_PANEL_BUTTON_CLICK_BG
    if over:
        return ATTR_PANEL_BUTTON_HOVER_BG
    return ATTR_PANEL_BUTTON_BG

def paint_button(painter: QPainter, fm, sp, x_left: float, baseline: float,
                 x_right: float, m: dict) -> AttrRow:
    label = apply_overlay_case(sp.label)
    tw = fm.horizontalAdvance(label)
    bx = x_left
    bw = max(1.0, x_right - x_left)
    top = baseline - fm.ascent()
    bh = fm.height() * ATTR_PANEL_BUTTON_H_SCALE
    painter.setPen(qcolor_from_hex(ATTR_PANEL_BUTTON_BORDER))
    painter.setBrush(qcolor_from_hex(_button_bg(sp, bx, top, bw, bh, m)))
    painter.drawRoundedRect(
        QRectF(bx, top, bw, bh), ATTR_PANEL_CORNER_RADIUS,
        ATTR_PANEL_CORNER_RADIUS)
    over = _button_over(bx, top, bw, bh, m)
    text_c = ATTR_PANEL_HOVER_COLOR if over else ATTR_PANEL_BUTTON_TEXT
    painter.setPen(qcolor_from_hex(text_c))
    text_y = top + (bh + fm.ascent() - fm.descent()) / 2
    painter.drawText(int(bx + (bw - tw) / 2), int(text_y), label)
    return AttrRow(sp, bx, top, bw, bh)
