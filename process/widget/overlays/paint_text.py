from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter

from process.common.font import make_font
from configs.settings_color import (
    LIVE_REC_INDICATOR_COLOR,
    OBJECT_LIST_HIDDEN_COLOR, OBJECT_LIST_HOVER_COLOR,
    OBJECT_LIST_SELECTED_COLOR,
    MESSAGE_OVERLAY_BG_COLOR, MESSAGE_OVERLAY_TEXT_COLOR,
    OVERLAY_HICONTRAST_TEXT_COLOR,
    OVERLAY_SHADOW_COLOR, OVERLAY_TEXT_COLOR, OVERLAY_TEXT_SHADOW,
    REGION_LIST_HIDDEN_COLOR, REGION_LIST_HOVER_COLOR,
    REGION_LIST_SELECTED_COLOR,
)

REC_DOT_CHAR: str = '●'

BOLD_MARK: str = '\x02'

def draw_line_with_bold(
    painter: QPainter, x: int, baseline: int, cased: str, pen: QColor,
) -> None:
    orig_f = painter.font()
    painter.setPen(pen)
    cx = float(x)
    for i, part in enumerate(cased.split(BOLD_MARK)):
        if not part:
            continue
        seg_f = QFont(orig_f)
        seg_f.setBold(i % 2 == 1)
        painter.setFont(seg_f)
        painter.drawText(int(round(cx)), int(baseline), part)
        cx += QFontMetrics(seg_f).horizontalAdvance(part)
    painter.setFont(orig_f)

def draw_line_with_dot(
    painter: QPainter, x: int, baseline: int, cased: str,
    text_pen: QColor, dot_pen: QColor, dot_size: int | None = None,
) -> None:
    fm = painter.fontMetrics()
    idx = cased.find(REC_DOT_CHAR)
    if idx < 0:
        painter.setPen(text_pen)
        painter.drawText(int(x), int(baseline), cased)
        return
    pre = cased[:idx]
    post = cased[idx + 1:]
    pre_adv = fm.horizontalAdvance(pre)
    dot_adv = fm.horizontalAdvance(REC_DOT_CHAR)
    orig_f = painter.font()
    dot_f = QFont(orig_f)
    dot_f.setUnderline(False)
    if dot_size is not None:
        dot_f.setPointSize(int(dot_size))
    dot_fm = QFontMetrics(dot_f)
    lift = round(dot_fm.ascent() * REC_DOT_BASELINE_LIFT_RATIO)
    center_off = round((fm.capHeight() - dot_fm.capHeight()) * 0.5)
    dot_baseline = baseline - lift - center_off
    painter.setPen(text_pen)

    pre_draw = pre.rstrip()
    if pre_draw:
        painter.drawText(int(x), int(baseline), pre_draw)
    if post:
        painter.drawText(int(x + pre_adv + dot_adv), int(baseline), post)
    painter.setPen(dot_pen)
    painter.setFont(dot_f)
    painter.drawText(int(x + pre_adv), int(dot_baseline), REC_DOT_CHAR)
    painter.setFont(orig_f)
from configs.settings_overlay import (
    MESSAGE_OVERLAY_BG_ENABLE, MESSAGE_OVERLAY_BOLD, MESSAGE_OVERLAY_ITALIC,
    MESSAGE_OVERLAY_LINEHEIGHT, OVERLAY_LINE_PAD, OVERLAY_TEXT_BOLD,
    OVERLAY_TEXT_ITALIC, OVERLAY_TEXT_LINEHEIGHT, REC_DOT_BASELINE_LIFT_RATIO,
    REGION_LIST_SELECTED_BOLD, REGION_LIST_SELECTED_UNDERLINE,
    PANEL_TITLE_GAP_RATIO, STATUS_OVERLAY_LINEHEIGHT,
)
from process.mode import HICONTRAST_OVERLAY_MODES
from process.widget.overlays._layout import (
    ROLE_AUDIO_HEAD, ROLE_AUDIO_ITEM,
    ROLE_MESSAGE, ROLE_OBJECT_HEAD, ROLE_OBJECT_ITEM,
    ROLE_REGION_HEAD, ROLE_REGION_ITEM, ROLE_STATUS, ROLE_STATUS_HEAD,
    build_overlay_lines, line_metrics, object_sole_visible_index,
    slot_baseline,
)
from process.widget.qt_paint import qcolor_from_hex
from process.widget.scale import (
    scaled_margin, scaled_message_size, scaled_status_size,
    scaled_text_size, scaled_title_size,
)
from process.widget.text_case import apply_overlay_case

def _region_item_state(item: tuple) -> tuple[bool, bool]:
    selected = bool(item[1]) if len(item) > 1 else False
    visible = bool(item[2]) if len(item) > 2 else True
    return selected, visible

def _list_item_color(
    selected: bool, visible: bool, base_color: str,
    selected_color: str, hidden_color: str,
) -> str:
    if selected:
        return selected_color
    if not visible:
        return hidden_color
    return base_color

def paint_overlay_text(
    painter: QPainter,
    info_overlay: str,
    cam_overlay: str,
    objinfo_overlay: str,
    status_overlay: str,
    stat_overlay: str,
    w: int,
    render_mode: int = 0,
    region_items: list | None = None,
    object_items: list | None = None,
    message: str = '',
    region_hover: int | None = None,
    object_hover: int | None = None,
    audio_items: list | None = None,
    audio_hover: int | None = None,
) -> tuple[list, list, list]:
    painter.save()
    text_size = scaled_text_size(w)
    title_size = scaled_title_size(w)
    msg_size = scaled_message_size(w)
    f = make_font()
    f.setPointSize(text_size)
    f.setBold(OVERLAY_TEXT_BOLD)
    f.setItalic(OVERLAY_TEXT_ITALIC)
    painter.setFont(f)
    fm = painter.fontMetrics()
    y0, lh, gap, pad_left = line_metrics(painter, w)

    _mf = make_font()
    _mf.setPointSize(msg_size)
    _mf.setBold(MESSAGE_OVERLAY_BOLD)
    _mf.setItalic(MESSAGE_OVERLAY_ITALIC)
    _msg_lh = MESSAGE_OVERLAY_LINEHEIGHT or OVERLAY_TEXT_LINEHEIGHT
    msg_extra = (round(QFontMetrics(_mf).height() * _msg_lh)
                 + OVERLAY_LINE_PAD) - lh

    status_size = scaled_status_size(w)
    _sf = make_font()
    _sf.setPointSize(status_size)
    _sf.setBold(OVERLAY_TEXT_BOLD)
    _sf.setItalic(OVERLAY_TEXT_ITALIC)
    _status_lh = STATUS_OVERLAY_LINEHEIGHT or OVERLAY_TEXT_LINEHEIGHT
    status_extra = (round(QFontMetrics(_sf).height() * _status_lh)
                    + OVERLAY_LINE_PAD) - lh
    shd = qcolor_from_hex(OVERLAY_SHADOW_COLOR)
    if render_mode in HICONTRAST_OVERLAY_MODES:
        base_color = OVERLAY_HICONTRAST_TEXT_COLOR
    else:
        base_color = OVERLAY_TEXT_COLOR

    def _draw(text, x, y, color, emphasize=False, is_status_head=False,
              is_region_head=False, hover=False, is_message=False,
              is_status=False):
        styled = (emphasize or is_status_head or is_region_head or hover
                  or is_message or is_status)
        if styled:
            if is_message:

                f.setPointSize(msg_size)
                f.setBold(MESSAGE_OVERLAY_BOLD)
                f.setItalic(MESSAGE_OVERLAY_ITALIC)
            elif is_status:

                f.setPointSize(status_size)
            elif is_status_head:
                f.setPointSize(title_size)
                f.setBold(True)
                f.setUnderline(REGION_LIST_SELECTED_UNDERLINE)
            elif is_region_head:

                f.setPointSize(title_size)
                f.setBold(True)

            elif hover:

                f.setBold(True)
            else:

                f.setBold(REGION_LIST_SELECTED_BOLD)

            painter.setFont(f)
        cased = apply_overlay_case(text)
        if is_message and MESSAGE_OVERLAY_BG_ENABLE:
            mfm = painter.fontMetrics()
            tw = mfm.horizontalAdvance(cased)
            ph = scaled_margin(w, 6)
            pv = scaled_margin(w, 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(qcolor_from_hex(MESSAGE_OVERLAY_BG_COLOR)))
            painter.drawRoundedRect(
                x - ph, y - mfm.ascent() - pv,
                tw + ph * 2, mfm.height() + pv * 2, 4, 4,
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
        if BOLD_MARK in cased:

            if OVERLAY_TEXT_SHADOW:
                draw_line_with_bold(painter, x + 1, y + 1, cased, shd)
            draw_line_with_bold(
                painter, x, y, cased, qcolor_from_hex(color))
        else:
            if OVERLAY_TEXT_SHADOW:
                draw_line_with_dot(painter, x + 1, y + 1, cased, shd, shd,
                                   text_size)
            draw_line_with_dot(painter, x, y, cased,
                               qcolor_from_hex(color),
                               qcolor_from_hex(LIVE_REC_INDICATOR_COLOR),
                               text_size)
        if styled:
            f.setUnderline(False)
            f.setBold(OVERLAY_TEXT_BOLD)
            f.setItalic(OVERLAY_TEXT_ITALIC)
            f.setPointSize(text_size)
            painter.setFont(f)
        return cased
    texts = {
        'info': info_overlay, 'stat': stat_overlay,
        'cam': cam_overlay, 'objinfo': objinfo_overlay,
        'status': status_overlay,
    }
    rows: list = []
    object_rows: list = []
    audio_rows: list = []
    obj_sole_idx = object_sole_visible_index(object_items)
    lines = build_overlay_lines(
        texts, region_items, object_items, message, audio_items,
    )

    title_body_gap = round(fm.height() * PANEL_TITLE_GAP_RATIO)
    extra_y = 0
    for slot, ln in enumerate(lines):

        if ln['role'] == ROLE_MESSAGE:
            extra_y += msg_extra
        elif ln['role'] == ROLE_STATUS:
            extra_y += status_extra
        y = slot_baseline(y0, lh, gap, slot) + extra_y
        color = base_color
        emphasize = False
        hover = False
        is_status_head = (ln['role'] == ROLE_STATUS_HEAD)
        is_region_head = ln['role'] in (
            ROLE_REGION_HEAD, ROLE_OBJECT_HEAD, ROLE_AUDIO_HEAD)
        if ln['role'] == ROLE_REGION_ITEM and region_items is not None:
            selected, visible = _region_item_state(region_items[ln['index']])
            color = _list_item_color(
                selected, visible, base_color,
                REGION_LIST_SELECTED_COLOR, REGION_LIST_HIDDEN_COLOR,
            )
            emphasize = selected
            if not selected and region_hover == ln['index']:
                color = REGION_LIST_HOVER_COLOR
                hover = True
        elif ln['role'] == ROLE_AUDIO_ITEM and audio_items is not None:
            selected, visible = _region_item_state(audio_items[ln['index']])
            color = _list_item_color(
                selected, visible, base_color,
                REGION_LIST_SELECTED_COLOR, REGION_LIST_HIDDEN_COLOR,
            )
            emphasize = selected
            if not selected and audio_hover == ln['index']:
                color = REGION_LIST_HOVER_COLOR
                hover = True
        elif ln['role'] == ROLE_OBJECT_ITEM and object_items is not None:
            selected, visible = _region_item_state(object_items[ln['index']])
            color = _list_item_color(
                selected, visible, base_color,
                OBJECT_LIST_SELECTED_COLOR, OBJECT_LIST_HIDDEN_COLOR,
            )
            emphasize = selected or ln['index'] == obj_sole_idx
            if not selected and object_hover == ln['index']:
                color = OBJECT_LIST_HOVER_COLOR
                hover = True
        elif ln['role'] == ROLE_MESSAGE:
            if (MESSAGE_OVERLAY_TEXT_COLOR == OVERLAY_TEXT_COLOR
                    and render_mode in HICONTRAST_OVERLAY_MODES):
                color = OVERLAY_HICONTRAST_TEXT_COLOR
            else:
                color = MESSAGE_OVERLAY_TEXT_COLOR
        cased = _draw(ln['text'], pad_left, y, color, emphasize,
                      is_status_head, is_region_head, hover,
                      is_message=(ln['role'] == ROLE_MESSAGE),
                      is_status=(ln['role'] == ROLE_STATUS))
        if is_status_head or is_region_head:
            extra_y += title_body_gap
        if ln['role'] == ROLE_REGION_ITEM:
            tw = fm.horizontalAdvance(cased)
            rows.append((pad_left, y - fm.ascent(), tw,
                         fm.height(), ln['index']))
        elif ln['role'] == ROLE_OBJECT_ITEM:
            tw = fm.horizontalAdvance(cased)
            object_rows.append((pad_left, y - fm.ascent(), tw,
                                fm.height(), ln['index']))
        elif ln['role'] == ROLE_AUDIO_ITEM:
            tw = fm.horizontalAdvance(cased)
            audio_rows.append((pad_left, y - fm.ascent(), tw,
                               fm.height(), ln['index']))
    painter.restore()
    return rows, object_rows, audio_rows
