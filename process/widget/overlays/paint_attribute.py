from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFontMetrics, QPainter

from process.common.font import make_font
from configs.settings_attr import (
    ATTR_PANEL_BG_ALPHA, ATTR_PANEL_BG_COLOR,
    ATTR_PANEL_CORNER_RADIUS, ATTR_PANEL_CURVE_ROWS,
    ATTR_PANEL_LABEL_COLOR, ATTR_PANEL_TITLE_COLOR,
)
from configs.settings_color import ATTR_PANEL_SEPARATOR_COLOR
from configs.settings_overlay import OVERLAY_TEXT_BOLD, OVERLAY_TEXT_ITALIC
from process.widget.overlays.attr_spec import (
    KIND_BUTTON, KIND_CURVE, KIND_CUSTOM,
)
from process.widget.overlays.paint_attr_button import paint_button_row
from process.widget.overlays.paint_attr_control import paint_control
from process.widget.overlays.paint_attr_curve import paint_curve
from process.widget.overlays.paint_attr_metrics import (
    _is_collapsed, _panel_metrics, attr_row_line_h,
)
from process.widget.overlays.paint_text import draw_line_with_dot
from process.widget.qt_paint import qcolor_from_hex
from process.widget.scale import scaled_text_size, scaled_title_size
from process.widget.text_case import apply_overlay_case

def _panel_fonts(w: int) -> tuple:
    f = make_font()
    f.setPointSize(scaled_text_size(w))
    f.setBold(OVERLAY_TEXT_BOLD)
    f.setItalic(OVERLAY_TEXT_ITALIC)
    title_f = make_font()
    title_f.setPointSize(scaled_title_size(w))
    title_f.setBold(True)
    title_f.setItalic(OVERLAY_TEXT_ITALIC)
    return f, title_f

def attr_line_height(w: int) -> int:
    f, _ = _panel_fonts(w)
    return attr_row_line_h(QFontMetrics(f))

def measure_attribute_panel(
    w: int, sections: list, collapsed: dict | None = None,
) -> tuple:
    blocks = [(s.title_text(), s.specs())
              for s in sorted(sections, key=lambda s: getattr(s, 'order', 0))]
    blocks = [(t, sp) for t, sp in blocks if sp]
    if not blocks:
        return (0, 0)
    f, title_f = _panel_fonts(w)
    m = _panel_metrics(
        None, w, blocks, QFontMetrics(f), QFontMetrics(title_f), collapsed)
    return (m['panel_w'], m['panel_h'])

def paint_attribute_sections(
    painter: QPainter, w: int, h: int, sections: list,
    mouse_pos: tuple | None = None, pressed_label: str | None = None,
    collapsed: dict | None = None, widget=None,
    origin: tuple | None = None,
) -> list:
    blocks = [(s.title_text(), s.specs())
              for s in sorted(sections, key=lambda s: getattr(s, 'order', 0))]
    blocks = [(t, sp) for t, sp in blocks if sp]
    if not blocks:
        if widget is not None:
            widget._attr_panel_rect = None
        return []
    painter.save()
    f, title_f = _panel_fonts(w)
    painter.setFont(title_f)
    title_fm = painter.fontMetrics()
    painter.setFont(f)
    fm = painter.fontMetrics()
    metrics = _panel_metrics(painter, w, blocks, fm, title_fm, collapsed)
    if origin is not None:
        metrics['x0'], metrics['y0'] = origin
    metrics['mouse'] = mouse_pos
    metrics['pressed'] = pressed_label
    metrics['collapsed'] = collapsed
    _paint_bg(painter, metrics)
    rows = _paint_blocks(painter, blocks, fm, f, title_f, metrics)
    if widget is not None:
        widget._attr_panel_rect = (
            metrics['x0'], metrics['y0'],
            metrics['panel_w'], metrics['panel_h'],
        )
    painter.restore()
    return rows

def _paint_bg(painter: QPainter, m: dict) -> None:
    bg = qcolor_from_hex(ATTR_PANEL_BG_COLOR)
    bg.setAlpha(ATTR_PANEL_BG_ALPHA)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(bg)
    painter.drawRoundedRect(
        QRectF(m['x0'], m['y0'], m['panel_w'], m['panel_h']),
        ATTR_PANEL_CORNER_RADIUS, ATTR_PANEL_CORNER_RADIUS,
    )

def _paint_hline(painter: QPainter, m: dict, y: float) -> None:
    painter.setPen(qcolor_from_hex(ATTR_PANEL_SEPARATOR_COLOR))
    x1 = m['x0'] + m['pad']
    x2 = m['x0'] + m['panel_w'] - m['pad']
    painter.drawLine(int(x1), int(y), int(x2), int(y))

def _sep_y(baseline: float, fm, m: dict, advance: float) -> float:
    line_extra = max(0, m['line_h'] - fm.height())
    return baseline - m['ascent'] - (advance + line_extra) / 2

def _paint_blocks(painter: QPainter, blocks: list, fm, body_f, title_f,
                  m: dict) -> list:
    rows: list = []
    tx = m['x0'] + m['pad']
    baseline = m['y0'] + m['pad'] + m['ascent']
    title_c = qcolor_from_hex(ATTR_PANEL_TITLE_COLOR)
    label_c = qcolor_from_hex(ATTR_PANEL_LABEL_COLOR)
    sep_gap = m['sep_gap']
    for bi, (title, specs) in enumerate(blocks):
        if bi > 0 and title:

            advance = m['block_gap'] + sep_gap
            baseline += advance
            _paint_hline(painter, m, _sep_y(baseline, fm, m, advance))
        if title:
            painter.setFont(title_f)
            draw_line_with_dot(painter, int(tx), int(baseline),
                               apply_overlay_case(title), title_c, title_c,
                               body_f.pointSize())
            baseline += m['line_h'] + m['title_gap']
        painter.setFont(body_f)
        i = 0
        _row_start = len(rows)
        while i < len(specs):
            sp = specs[i]
            if sp.kind == KIND_BUTTON:
                run = [specs[i]]
                i += 1
                while (i < len(specs) and specs[i].kind == KIND_BUTTON
                       and not specs[i].row_break):
                    run.append(specs[i])
                    i += 1

                baseline += sep_gap
                _paint_hline(painter, m, _sep_y(baseline, fm, m, sep_gap))
                rows.extend(paint_button_row(painter, fm, run, baseline, m))
                baseline += m['line_h'] + m['btn_extra_h']
                continue
            if sp.kind == KIND_CURVE:

                if i > 0 and specs[i - 1].kind != KIND_CURVE:
                    baseline += sep_gap
                    _paint_hline(painter, m, _sep_y(baseline, fm, m, sep_gap))
                col = _is_collapsed(m.get('collapsed'), sp)
                rows.extend(
                    paint_curve(painter, fm, sp, tx, baseline, m, col))
                span = 1 if col else (1 + ATTR_PANEL_CURVE_ROWS)
                baseline += m['line_h'] * span

                if not col:
                    baseline += sep_gap
                i += 1

                if i < len(specs):
                    baseline += sep_gap
                    _paint_hline(painter, m, _sep_y(baseline, fm, m, sep_gap))
                continue
            if sp.kind == KIND_CUSTOM:

                if i > 0:
                    baseline += sep_gap
                    _paint_hline(painter, m, _sep_y(baseline, fm, m, sep_gap))
                box_x = tx
                box_y = baseline - m['ascent']
                box_w = m['panel_w'] - m['pad'] * 2
                box_h = m['line_h'] * sp.custom_rows
                if sp.custom_paint is not None:
                    sp.custom_paint(painter, QRectF(box_x, box_y, box_w, box_h))
                baseline += box_h
                i += 1

                if i < len(specs):
                    baseline += m['line_h']
                continue

            painter.setPen(label_c)
            painter.drawText(
                int(tx), int(baseline), apply_overlay_case(sp.label))
            r = paint_control(painter, fm, sp, tx, baseline, m)
            if r is not None:
                rows.append(r)
            baseline += m['line_h']
            i += 1
        for _r in rows[_row_start:]:
            _r.section = title
    return rows
