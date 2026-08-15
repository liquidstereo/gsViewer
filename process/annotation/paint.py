import logging

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QBrush, QPainter, QPen

from process.common.font import make_font
from configs.settings_annot import (
    ANNOT_LINE_WIDTH, ANNOT_PIN_BORDER_WIDTH, ANNOT_PIN_LINE_H,
    ANNOT_PIN_R, ANNOT_TEXT_PAD,
)
from configs.settings_color import (
    ANNOT_LINE_ALPHA, ANNOT_LINE_COLOR, ANNOT_PIN_BORDER_COLOR,
    ANNOT_PIN_FILL_COLOR, ANNOT_TEXT_BG_ALPHA, ANNOT_TEXT_BG_COLOR,
    ANNOT_TEXT_FG_COLOR,
)
from process.widget.qt_paint import qcolor_from_hex

logger = logging.getLogger(__name__)

_PIN_R: int = ANNOT_PIN_R
_PIN_LINE_H: int = ANNOT_PIN_LINE_H
_TEXT_PAD: int = ANNOT_TEXT_PAD
_PIN_FILL = qcolor_from_hex(ANNOT_PIN_FILL_COLOR)
_PIN_BORDER = qcolor_from_hex(ANNOT_PIN_BORDER_COLOR)
_TEXT_BG = qcolor_from_hex(ANNOT_TEXT_BG_COLOR, ANNOT_TEXT_BG_ALPHA)
_TEXT_FG = qcolor_from_hex(ANNOT_TEXT_FG_COLOR)
_LINE_CLR = qcolor_from_hex(ANNOT_LINE_COLOR, ANNOT_LINE_ALPHA)

def paint_annotations(
    painter: QPainter,
    markers: list[tuple[int, int, str]],
) -> None:
    if not markers:
        return
    painter.save()
    f = make_font()
    f.setPointSize(10)
    f.setBold(True)
    painter.setFont(f)
    fm = painter.fontMetrics()

    for sx, sy, label in markers:
        top_y = sy - _PIN_R - _PIN_LINE_H

        painter.setPen(QPen(_PIN_BORDER, ANNOT_PIN_BORDER_WIDTH))
        painter.setBrush(QBrush(_PIN_FILL))
        painter.drawEllipse(
            sx - _PIN_R, sy - _PIN_R,
            _PIN_R * 2, _PIN_R * 2,
        )

        painter.setPen(QPen(_LINE_CLR, ANNOT_LINE_WIDTH))
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
