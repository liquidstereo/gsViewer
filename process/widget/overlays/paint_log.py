import logging

from PySide6.QtGui import QPainter

from process.common.font import make_font
from configs.settings_color import (
    OVERLAY_LOG_COLOR, OVERLAY_LOG_ERROR_COLOR, OVERLAY_LOG_WARNING_COLOR,
    OVERLAY_SHADOW_COLOR, OVERLAY_TEXT_SHADOW,
)
from configs.settings_overlay import (
    LOG_OVERLAY_LINEHEIGHT, LOG_OVERLAY_MAX_CHARS, OVERLAY_LINE_PAD,
    OVERLAY_LOG_BOLD, OVERLAY_LOG_ITALIC, OVERLAY_TEXT_LINEHEIGHT,
    OVERLAY_MARGIN,
)
from process.widget.qt_paint import qcolor_from_hex
from process.widget.scale import scaled_log_size, scaled_margin

def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 1 or len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + '...'

def paint_log_overlay(
    painter: QPainter, log_lines: list, w: int, h: int,
) -> None:
    lines = list(log_lines)
    painter.save()
    f = make_font()
    f.setPointSize(scaled_log_size(w))
    f.setBold(OVERLAY_LOG_BOLD)
    f.setItalic(OVERLAY_LOG_ITALIC)
    painter.setFont(f)
    fm = painter.fontMetrics()
    line_h = (round(fm.height() * (LOG_OVERLAY_LINEHEIGHT
                                   or OVERLAY_TEXT_LINEHEIGHT))
              + OVERLAY_LINE_PAD)
    pad_left = scaled_margin(w, OVERLAY_MARGIN)
    pad_bot = scaled_margin(w, OVERLAY_MARGIN)
    y = h - fm.descent() - pad_bot
    shadow = qcolor_from_hex(OVERLAY_SHADOW_COLOR)
    for levelno, line in reversed(lines):
        if levelno >= logging.ERROR:
            hex_c = OVERLAY_LOG_ERROR_COLOR
        elif levelno >= logging.WARNING:
            hex_c = OVERLAY_LOG_WARNING_COLOR
        else:
            hex_c = OVERLAY_LOG_COLOR
        text_c = qcolor_from_hex(hex_c)
        text = _truncate(line, LOG_OVERLAY_MAX_CHARS)
        if OVERLAY_TEXT_SHADOW:
            painter.setPen(shadow)
            painter.drawText(pad_left + 1, y + 1, text)
        painter.setPen(text_c)
        painter.drawText(pad_left, y, text)
        y -= line_h
    painter.restore()
