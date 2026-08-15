import time

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter

from process.common.font import make_font
from configs.settings_overlay import (
    LOADING_OVERLAY_BOLD, LOADING_OVERLAY_ITALIC, LOADING_OVERLAY_BLINK_PERIOD,
)
from configs.settings_attr import (
    ATTR_PANEL_BG_ALPHA, ATTR_PANEL_BG_COLOR,
    ATTR_PANEL_CORNER_RADIUS, ATTR_PANEL_TITLE_COLOR,
)
from process.widget.qt_paint import qcolor_from_hex
from process.widget.scale import scaled_loading_size, scaled_margin

_BG_PAD_X = 24
_BG_PAD_Y = 14

def _blink_on() -> bool:
    period = LOADING_OVERLAY_BLINK_PERIOD
    if period <= 0:
        return True
    return (time.perf_counter() % period) / period < 0.5

def paint_loading_overlay(
    painter: QPainter, w: int, h: int, text: str,
) -> None:
    if not text:
        return
    painter.save()
    f = make_font()
    f.setPointSize(scaled_loading_size(w))
    f.setBold(LOADING_OVERLAY_BOLD)
    f.setItalic(LOADING_OVERLAY_ITALIC)
    painter.setFont(f)
    fm = painter.fontMetrics()
    pad_x = scaled_margin(w, _BG_PAD_X)
    pad_y = scaled_margin(w, _BG_PAD_Y)
    box_w = fm.horizontalAdvance(text) + 2 * pad_x
    box_h = fm.height() + 2 * pad_y
    rect = QRectF((w - box_w) / 2.0, (h - box_h) / 2.0, box_w, box_h)
    bg = qcolor_from_hex(ATTR_PANEL_BG_COLOR)
    bg.setAlpha(ATTR_PANEL_BG_ALPHA)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(bg)
    painter.drawRoundedRect(
        rect, ATTR_PANEL_CORNER_RADIUS, ATTR_PANEL_CORNER_RADIUS,
    )
    if _blink_on():
        painter.setPen(qcolor_from_hex(ATTR_PANEL_TITLE_COLOR))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()
