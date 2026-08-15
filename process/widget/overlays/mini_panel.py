from typing import Callable

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFontMetrics, QPainter

from configs.settings_attr import (
    ATTR_PANEL_BG_ALPHA, ATTR_PANEL_BG_COLOR, ATTR_PANEL_CORNER_RADIUS,
    ATTR_PANEL_PAD, ATTR_PANEL_TITLE_COLOR,
)
from configs.settings_overlay import PANEL_TITLE_GAP_RATIO
from process.widget.overlays.paint_attribute import (
    _panel_fonts, attr_line_height,
)
from process.widget.qt_paint import qcolor_from_hex
from process.widget.scale import scaled_margin
from process.widget.text_case import apply_overlay_case

def mini_panel_metrics(w: int, content_rows: int) -> dict:
    pad = scaled_margin(w, ATTR_PANEL_PAD)
    line_h = attr_line_height(w)
    body_f, title_f = _panel_fonts(w)
    body_fm = QFontMetrics(body_f)
    title_gap = round(body_fm.height() * PANEL_TITLE_GAP_RATIO)
    content_h = max(1, line_h * content_rows)
    panel_h = pad * 2 + line_h + title_gap + content_h
    return {
        'pad': pad, 'line_h': line_h, 'title_gap': title_gap,
        'content_h': content_h, 'panel_h': panel_h,
        'body_f': body_f, 'title_f': title_f, 'ascent': body_fm.ascent(),
    }

def mini_panel_height(w: int, content_rows: int) -> int:
    return int(mini_panel_metrics(w, content_rows)['panel_h'])

def paint_mini_panel(
    painter: QPainter, w: int, x0: float, y0: float, panel_w: int,
    title: str, content_rows: int,
    content_paint: Callable[[QPainter, QRectF], None], alpha: float = 1.0,
) -> QRectF:
    m = mini_panel_metrics(w, content_rows)
    pad = m['pad']
    painter.save()
    painter.setOpacity(alpha)
    bg = qcolor_from_hex(ATTR_PANEL_BG_COLOR)
    bg.setAlpha(ATTR_PANEL_BG_ALPHA)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(bg)
    painter.drawRoundedRect(
        QRectF(x0, y0, panel_w, m['panel_h']),
        ATTR_PANEL_CORNER_RADIUS, ATTR_PANEL_CORNER_RADIUS,
    )
    painter.setFont(m['title_f'])
    painter.setPen(qcolor_from_hex(ATTR_PANEL_TITLE_COLOR))
    painter.drawText(
        int(x0 + pad), int(y0 + pad + m['ascent']),
        apply_overlay_case(title),
    )
    box_y = y0 + pad + m['line_h'] + m['title_gap']
    box_rect = QRectF(x0 + pad, box_y, panel_w - pad * 2, m['content_h'])
    content_paint(painter, box_rect)
    painter.restore()
    return box_rect
