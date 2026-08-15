import logging

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QBrush, QFont, QFontMetrics, QPainter

from process.common.font import make_font
from configs.settings_color import (
    HELP_DESC_COLOR, HELP_HEADER_COLOR, HELP_KEY_COLOR,
    HELP_PANEL_BG_ALPHA, HELP_PANEL_BG_COLOR, HELP_TITLE_COLOR,
)
from process.widget.qt_paint import qcolor_from_hex

logger = logging.getLogger(__name__)

_BG = qcolor_from_hex(HELP_PANEL_BG_COLOR, HELP_PANEL_BG_ALPHA)
_TITLE_CLR = qcolor_from_hex(HELP_TITLE_COLOR)
_HDR_CLR = qcolor_from_hex(HELP_HEADER_COLOR)
_KEY_CLR = qcolor_from_hex(HELP_KEY_COLOR)
_DESC_CLR = qcolor_from_hex(HELP_DESC_COLOR)

_PAD = 22
_COL_GAP = 28
_ROW_H = 17
_SEC_GAP = 7

_KEY_DESC_GAP = 16

_KEY_W_MIN = 56

_DESC_W = 142

_DESC_PAD = 16
_TITLE_H = 26
_TITLE_GAP = 10
_RADIUS = 10

_PLAYBACK_SEC: tuple[str, list] = ('PLAYBACK', [
    ('Space', 'Play / Pause'),
    ('<- / ->', 'Prev / Next frame'),
    ('↑ / ↓', 'First / Last frame'),
    ('Esc', 'Quit'),
])

_VIEW_SEC: tuple[str, list] = ('VIEW', [
    ('F1', 'This help'),
    ('F2', 'Plugin help'),
    ('/', 'Toggle all overlays'),
    ('U', 'Compact overlays (FPS)'),
    (',', 'Sequence inset'),
    (';', 'Attribute panel'),
    ('Shift+B', 'Corner bracket'),
    ("'", 'Bbox + Grid'),
    ('C', 'Colormap'),
    ('B', 'Depth occlusion'),
    ('.', 'Logs'),
    ('F', 'Fog'),
    ('Tab', 'Cycle World Rotation'),
    ('Ctrl+Home', 'Reset all & clear saved'),
    ('Alt+Shift+R', 'Reset camera'),
    ('Num.', 'Turntable'),
])

_SCREENSHOT_SEC: tuple[str, list] = ('SCREENSHOT', [
    ('`', 'Save screenshot'),
    ('Ctrl+R', 'Live record toggle'),
])

_ORTHO_SEC: tuple[str, list] = ('ORTHO VIEW (toggle)', [
    ('F5', 'Front'),
    ('F6', 'Back'),
    ('F7', 'Left'),
    ('F8', 'Right'),
    ('F9', 'Top'),
    ('F10', 'Bottom'),
])

_MAIN_OBJ_SEC: tuple[str, list] = ('MAIN OBJECT', [
    ('W', 'Translate'),
    ('E', 'Rotate'),
    ('R', 'Scale'),
    ('L', 'Lock toggle'),
    ('H', 'Hide toggle'),
    ('S', 'Solo toggle (selected only)'),
    ('Alt+1~9', 'Isolate input N'),
    ('Alt+R', 'Reset transform'),
])

_MOUSE_SEC: tuple[str, list] = ('MOUSE', [
    ('RMB', 'Context menu (objects + regions)'),
])

_RENDER_MODE_SEC: tuple[str, list] = ('RENDER MODE', [
    ('Q', 'Default'),
    ('1', 'Normal'),
    ('2', 'Point'),
    ('3', 'Aniso'),
    ('4', 'Opacity'),
    ('5', 'Hit Count'),
    ('6', 'Accumulation'),
    ('7', 'Scale'),
    ('8', 'SH'),
    ('9', 'Rotation'),
    ('0', 'Median Depth'),
    ('[ / ]', 'Splat size'),
    ('\\', 'Reset size'),
    ('Ctrl+[ / ]', 'Slice ratio down / up'),
    ('Ctrl+\\', 'Reset slice ratio'),
])

_CAMERA_KF_SEC: tuple[str, list] = ('CAMERA KEYFRAME', [
    ('Alt+Shift+A', 'Add Camera Keyframe'),
    ('Alt+Shift+D', 'Remove Last Keyframe'),
    ('Alt+Shift+Del', 'Clear all Camera Keyframes'),
    ('Alt+Shift+P', 'Toggle Annotation Visible'),
    ('Alt+Shift+PgUp', 'Prev Camera Keyframe'),
    ('Alt+Shift+PgDn', 'Next Camera Keyframe'),
])

_OBJECT_KF_SEC: tuple[str, list] = ('OBJECT KEYFRAME', [
    ('Alt+A', 'Add Object Keyframe'),
    ('Alt+D', 'Remove Last Keyframe'),
    ('Alt+Del', 'Clear all Object Keyframes'),
    ('Alt+P', 'Toggle Object Markers Visible'),
    ('Alt+PgUp', 'Prev Object Keyframe'),
    ('Alt+PgDn', 'Next Object Keyframe'),
])

_GLOBAL_KF_SEC: tuple[str, list] = ('GLOBAL KEYFRAME', [
    ('A', 'Add Global Keyframe (objects + regions)'),
    ('D', 'Remove Last Keyframe'),
    ('Ctrl+Del', 'Clear all Global Keyframes'),
    ('P', 'Toggle Global Markers Visible'),
    ('Ctrl+PgUp', 'Prev Global Keyframe'),
    ('Ctrl+PgDn', 'Next Global Keyframe'),
])

_PAGES: list[tuple[list, list]] = [
    ([_PLAYBACK_SEC, _MAIN_OBJ_SEC, _MOUSE_SEC],
     [_SCREENSHOT_SEC, _ORTHO_SEC]),
    ([_VIEW_SEC], [_RENDER_MODE_SEC]),
    ([_GLOBAL_KF_SEC], []),
    ([_CAMERA_KF_SEC], [_OBJECT_KF_SEC]),
]
HELP_PAGE_COUNT: int = len(_PAGES)

def _secs_h(secs: list[tuple[str, list]]) -> int:
    h = 0
    for i, (_, entries) in enumerate(secs):
        if i > 0:
            h += _SEC_GAP
        h += _ROW_H * (1 + len(entries))
    return h

def _key_col_w(
    body_f: QFont,
    l_secs: list[tuple[str, list]],
    r_secs: list[tuple[str, list]],
) -> int:
    fm = QFontMetrics(body_f)
    widest = 0
    for secs in (l_secs, r_secs):
        for _, entries in secs:
            for key, _ in entries:
                widest = max(widest, fm.horizontalAdvance(key))
    return max(_KEY_W_MIN, widest + _KEY_DESC_GAP)

def _desc_col_w(
    body_f: QFont,
    l_secs: list[tuple[str, list]],
    r_secs: list[tuple[str, list]],
) -> int:
    fm = QFontMetrics(body_f)
    widest = 0
    for secs in (l_secs, r_secs):
        for _, entries in secs:
            for _, desc in entries:
                widest = max(widest, fm.horizontalAdvance(desc))
    return max(_DESC_W, widest + _DESC_PAD)

def _draw_secs(
    painter: QPainter,
    secs: list[tuple[str, list]],
    x: int,
    y: int,
    hdr_f: QFont,
    body_f: QFont,
    key_w: int,
) -> None:
    cy = y
    for i, (title, entries) in enumerate(secs):
        if i > 0:
            cy += _SEC_GAP
        painter.setFont(hdr_f)
        painter.setPen(_HDR_CLR)
        painter.drawText(x, cy + _ROW_H - 3, title)
        cy += _ROW_H
        painter.setFont(body_f)
        for key, desc in entries:
            painter.setPen(_KEY_CLR)
            painter.drawText(x, cy + _ROW_H - 3, key)
            painter.setPen(_DESC_CLR)
            painter.drawText(x + key_w, cy + _ROW_H - 3, desc)
            cy += _ROW_H

def _min_panel_w(
    title_f: QFont,
    hdr_f: QFont,
    title: str,
    l_secs: list[tuple[str, list]],
    r_secs: list[tuple[str, list]],
    content_w: int,
) -> int:
    need = QFontMetrics(title_f).horizontalAdvance(title)
    hfm = QFontMetrics(hdr_f)
    for secs in (l_secs, r_secs):
        for sec_title, _ in secs:
            need = max(need, hfm.horizontalAdvance(sec_title))
    return max(content_w, need + 2 * _PAD)

def _help_fonts() -> tuple[QFont, QFont, QFont]:
    body_f = make_font()
    body_f.setPointSize(9)
    title_f = make_font()
    title_f.setPointSize(11)
    title_f.setBold(True)
    hdr_f = make_font()
    hdr_f.setPointSize(9)
    hdr_f.setBold(True)
    return body_f, title_f, hdr_f

def _panel_w(
    body_f: QFont,
    title_f: QFont,
    hdr_f: QFont,
    title: str,
    l_secs: list[tuple[str, list]],
    r_secs: list[tuple[str, list]],
) -> int:
    key_w = _key_col_w(body_f, l_secs, r_secs)
    col_w = key_w + _desc_col_w(body_f, l_secs, r_secs)
    ncols = 2 if r_secs else 1
    content_w = ncols * col_w + (_COL_GAP if r_secs else 0) + 2 * _PAD
    return _min_panel_w(title_f, hdr_f, title, l_secs, r_secs, content_w)

def _paint_panel(
    painter: QPainter,
    w: int,
    h: int,
    title: str,
    l_secs: list[tuple[str, list]],
    r_secs: list[tuple[str, list]],
    fixed_w: int | None = None,
) -> None:
    body_f, title_f, hdr_f = _help_fonts()
    key_w = _key_col_w(body_f, l_secs, r_secs)
    col_w = key_w + _desc_col_w(body_f, l_secs, r_secs)
    if fixed_w is not None:
        panel_w = fixed_w
    else:
        panel_w = _panel_w(body_f, title_f, hdr_f, title, l_secs, r_secs)
    content_h = max(_secs_h(l_secs), _secs_h(r_secs)) if r_secs else _secs_h(l_secs)
    panel_h = _TITLE_H + _TITLE_GAP + content_h + 2 * _PAD

    px = (w - panel_w) // 2
    py = (h - panel_h) // 2

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(_BG))
    painter.drawRoundedRect(px, py, panel_w, panel_h, _RADIUS, _RADIUS)

    painter.setFont(title_f)
    painter.setPen(_TITLE_CLR)
    painter.drawText(
        QRect(px, py + _PAD, panel_w, _TITLE_H),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        title,
    )

    cy = py + _PAD + _TITLE_H + _TITLE_GAP
    _draw_secs(painter, l_secs, px + _PAD, cy, hdr_f, body_f, key_w)
    if r_secs:
        _draw_secs(
            painter, r_secs,
            px + _PAD + col_w + _COL_GAP, cy,
            hdr_f, body_f, key_w,
        )
    painter.restore()

def _help_uniform_w() -> int:
    body_f, title_f, hdr_f = _help_fonts()
    n = HELP_PAGE_COUNT
    widest = 0
    for i, (l_secs, r_secs) in enumerate(_PAGES):
        title = f'KEY  BINDINGS  {i + 1}/{n}   (<- / ->)'
        widest = max(
            widest,
            _panel_w(body_f, title_f, hdr_f, title, l_secs, r_secs),
        )
    return widest

def paint_help_overlay(
    painter: QPainter, w: int, h: int, page: int = 0,
) -> None:
    n = HELP_PAGE_COUNT
    page = max(0, min(page, n - 1))
    l_secs, r_secs = _PAGES[page]
    nav = '   (<- / ->)' if n > 1 else ''
    title = f'KEY  BINDINGS  {page + 1}/{n}{nav}'
    _paint_panel(
        painter, w, h, title, l_secs, r_secs, fixed_w=_help_uniform_w(),
    )

def paint_plugin_help_overlay(
    painter: QPainter,
    w: int,
    h: int,
    sections: list[tuple[str, list]],
    page: int = 0,
) -> None:
    if not sections:
        sections = [(
            'NO ACTIVE PLUGINS',
            [('--', 'Launch with -p <plugin>')],
        )]
    n = len(sections)
    page = max(0, min(page, n - 1))
    title, entries = sections[page]
    nav = '   (<- / ->)' if n > 1 else ''
    panel_title = f'PLUGIN HELP  {page + 1}/{n}{nav}'
    _paint_panel(painter, w, h, panel_title, [(title, entries)], [])
