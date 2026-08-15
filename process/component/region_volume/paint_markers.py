import logging

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from process.common.font import make_font
from process.component.region_volume.settings import (
    REGION_VOLUME_MARKER_BORDER_WIDTH, REGION_VOLUME_MARKER_LINE_ALPHA,
    REGION_VOLUME_MARKER_LINE_COLOR, REGION_VOLUME_MARKER_LINE_WIDTH,
    REGION_VOLUME_MARKER_PIN_BORDER, REGION_VOLUME_MARKER_PIN_FILL,
    REGION_VOLUME_MARKER_PIN_LINE_H, REGION_VOLUME_MARKER_PIN_R,
    REGION_VOLUME_MARKER_TEXT_BG, REGION_VOLUME_MARKER_TEXT_BG_ALPHA,
    REGION_VOLUME_MARKER_TEXT_FG, REGION_VOLUME_MARKER_TEXT_PAD,
    REGION_VOLUME_MARKER_TEXT_SIZE,
)
from process.widget.qt_paint import qcolor_from_hex

logger = logging.getLogger(__name__)

_PIN_R: int = REGION_VOLUME_MARKER_PIN_R
_PIN_LINE_H: int = REGION_VOLUME_MARKER_PIN_LINE_H
_TEXT_PAD: int = REGION_VOLUME_MARKER_TEXT_PAD
_DEFAULT_PIN_FILL = qcolor_from_hex(REGION_VOLUME_MARKER_PIN_FILL)
_PIN_BORDER = qcolor_from_hex(REGION_VOLUME_MARKER_PIN_BORDER)
_TEXT_BG = qcolor_from_hex(
    REGION_VOLUME_MARKER_TEXT_BG, REGION_VOLUME_MARKER_TEXT_BG_ALPHA)
_TEXT_FG = qcolor_from_hex(REGION_VOLUME_MARKER_TEXT_FG)
_DEFAULT_LINE_CLR = qcolor_from_hex(
    REGION_VOLUME_MARKER_LINE_COLOR, REGION_VOLUME_MARKER_LINE_ALPHA)

def _resolve_colors(color_hex: str | None) -> tuple[QColor, QColor]:
    if not color_hex:
        return _DEFAULT_PIN_FILL, _DEFAULT_LINE_CLR
    base = QColor(color_hex)
    if not base.isValid():
        return _DEFAULT_PIN_FILL, _DEFAULT_LINE_CLR
    line = QColor(base)
    line.setAlpha(REGION_VOLUME_MARKER_LINE_ALPHA)
    return base, line

def paint_region_volume_keyframes(
    painter: QPainter,
    markers: list[tuple[int, int, str]],
    color_hex: str | None = None,
) -> None:
    if not markers:
        return
    pin_fill, line_clr = _resolve_colors(color_hex)
    painter.save()
    f = make_font()
    f.setPointSize(REGION_VOLUME_MARKER_TEXT_SIZE)
    f.setBold(True)
    painter.setFont(f)
    fm = painter.fontMetrics()

    for sx, sy, label in markers:
        top_y = sy - _PIN_R - _PIN_LINE_H

        painter.setPen(QPen(_PIN_BORDER, REGION_VOLUME_MARKER_BORDER_WIDTH))
        painter.setBrush(QBrush(pin_fill))
        painter.drawEllipse(
            sx - _PIN_R, sy - _PIN_R,
            _PIN_R * 2, _PIN_R * 2,
        )

        painter.setPen(QPen(line_clr, REGION_VOLUME_MARKER_LINE_WIDTH))
        painter.drawLine(sx, sy - _PIN_R, sx, top_y)

        tw = fm.horizontalAdvance(label)
        th = fm.height()
        tx = sx - tw // 2
        bg = QRect(
            tx - _TEXT_PAD,
            top_y - th,
            tw + _TEXT_PAD * 2,
            th + _TEXT_PAD,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_TEXT_BG))
        painter.drawRoundedRect(bg, 3, 3)

        painter.setPen(_TEXT_FG)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawText(tx, top_y - _TEXT_PAD // 2, label)

    painter.restore()
