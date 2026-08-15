from PySide6.QtGui import QColor, QPainter

from process.common.font import make_font
from configs.settings_color import (
    LIVE_REC_INDICATOR_COLOR, MESSAGE_OVERLAY_TEXT_COLOR,
    OVERLAY_HICONTRAST_TEXT_COLOR,
    OVERLAY_SHADOW_COLOR, OVERLAY_TEXT_COLOR, OVERLAY_TEXT_SHADOW,
)
from configs.settings_overlay import (
    COMMENT_OVERLAY_LINEHEIGHT, COMMENT_OVERLAY_TEXT_BOLD,
    COMMENT_OVERLAY_TEXT_ITALIC, MESSAGE_OVERLAY_BOLD,
    MESSAGE_OVERLAY_BUF_CHAR, MESSAGE_OVERLAY_ITALIC, OVERLAY_LINE_PAD,
    OVERLAY_SEPARATOR_CHAR, OVERLAY_TEXT_LINEHEIGHT, OVERLAY_MARGIN,
)
from process.mode import HICONTRAST_OVERLAY_MODES
from process.widget.overlays.paint_text import draw_line_with_dot
from process.widget.qt_paint import qcolor_from_hex
from process.widget.scale import scaled_margin, scaled_comment_size
from process.widget.text_case import apply_overlay_case

def paint_comment_overlay(
    painter: QPainter, text: str, w: int, h: int,
    log_line_count: int, render_mode: int = 0, append_msg: str = '',
    dot_visible: bool = True,
) -> int:

    msg = apply_overlay_case(append_msg) if append_msg else ''
    painter.save()
    f = make_font()
    f.setPointSize(scaled_comment_size(w))
    f.setBold(COMMENT_OVERLAY_TEXT_BOLD)
    f.setItalic(COMMENT_OVERLAY_TEXT_ITALIC)
    painter.setFont(f)
    fm = painter.fontMetrics()
    line_h = (round(fm.height() * (COMMENT_OVERLAY_LINEHEIGHT
                                   or OVERLAY_TEXT_LINEHEIGHT))
              + OVERLAY_LINE_PAD)
    pad_left = scaled_margin(w, OVERLAY_MARGIN)
    pad_bot = scaled_margin(w, OVERLAY_MARGIN)
    base_y = h - fm.descent() - pad_bot
    y = base_y - line_h * log_line_count if log_line_count > 0 else base_y

    has_content = bool(text or append_msg)
    div_y = y - line_h if has_content else y
    color_hex = (
        OVERLAY_HICONTRAST_TEXT_COLOR
        if render_mode in HICONTRAST_OVERLAY_MODES
        else OVERLAY_TEXT_COLOR
    )
    shadow = qcolor_from_hex(OVERLAY_SHADOW_COLOR)
    text_c = qcolor_from_hex(color_hex)
    cased = apply_overlay_case(text) if text else ''

    seg = cased + MESSAGE_OVERLAY_BUF_CHAR if (cased and msg) else cased

    if OVERLAY_TEXT_SHADOW:
        painter.setPen(shadow)
        painter.drawText(pad_left + 1, div_y + 1, OVERLAY_SEPARATOR_CHAR)
        if seg:
            painter.drawText(pad_left + 1, y + 1, seg)
    painter.setPen(text_c)
    painter.drawText(pad_left, div_y, OVERLAY_SEPARATOR_CHAR)
    if seg:
        painter.drawText(pad_left, y, seg)
    if msg:

        mx = pad_left + fm.horizontalAdvance(seg)
        msg_font = make_font()
        msg_font.setPointSize(scaled_comment_size(w))
        msg_font.setBold(MESSAGE_OVERLAY_BOLD)
        msg_font.setItalic(MESSAGE_OVERLAY_ITALIC)
        painter.setFont(msg_font)

        transparent = QColor(0, 0, 0, 0)
        dot_c = (qcolor_from_hex(LIVE_REC_INDICATOR_COLOR)
                 if dot_visible else transparent)

        if (MESSAGE_OVERLAY_TEXT_COLOR == OVERLAY_TEXT_COLOR
                and render_mode in HICONTRAST_OVERLAY_MODES):
            msg_hex = OVERLAY_HICONTRAST_TEXT_COLOR
        else:
            msg_hex = MESSAGE_OVERLAY_TEXT_COLOR
        if OVERLAY_TEXT_SHADOW:
            draw_line_with_dot(
                painter, mx + 1, y + 1, msg, shadow,
                shadow if dot_visible else transparent)
        draw_line_with_dot(
            painter, mx, y, msg, qcolor_from_hex(msg_hex), dot_c)
    painter.restore()
    return line_h * 2 if has_content else line_h
