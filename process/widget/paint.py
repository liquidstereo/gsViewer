import numpy as np
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import (
    QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPolygon,
)

from process.common.font import make_font
from configs.settings_color import (
    BACKGROUND_COLOR,
    BBOX_COLOR,
    CMAP_BAR_BORDER_COLOR,
    GRID_AXIS_LABEL_COLOR, GRID_COLOR_FLOOR, GRID_COLOR_WALL_B,
    GRID_COLOR_WALL_L, GRID_TICK_COLOR,
)
from configs.settings_window import (
    ANTIALIAS,
    BBOX_LINE_ALPHA,
    GRID_LINE_ALPHA, GRID_PANE_ALPHA,
    STARTUP_GRID_LABELS, STARTUP_GRID_TICKS,
)
from process.common import build_depth_mask, hex_to_rgb
from process.widget.scale import (
    scaled_bbox_line_width, scaled_grid_line_width,
    scaled_seq_inset_margin, scaled_seq_inset_radius, scaled_seq_inset_w,
)

def begin_overlay(painter: QPainter) -> None:
    painter.setBackgroundMode(Qt.BGMode.TransparentMode)
    painter.setBrush(Qt.BrushStyle.NoBrush)

_GRID_FACE_COLORS: dict[str, str] = {
    'floor':  GRID_COLOR_FLOOR,
    'wall_l': GRID_COLOR_WALL_L,
    'wall_b': GRID_COLOR_WALL_B,
}

def _theme_refresh() -> None:

    _GRID_FACE_COLORS.update({
        'floor':  GRID_COLOR_FLOOR,
        'wall_l': GRID_COLOR_WALL_L,
        'wall_b': GRID_COLOR_WALL_B,
    })

_CMAP_CACHE: dict[str, np.ndarray] = {}
_BAR_H: int = 400
_BAR_W: int = 20
_BAR_TEXT_CLR: tuple = tuple(1.0 - c for c in hex_to_rgb(BACKGROUND_COLOR))

def _get_cmap_gradient(cmap: str) -> np.ndarray:
    if cmap not in _CMAP_CACHE:
        t = np.linspace(1.0, 0.0, _BAR_H)
        try:
            import matplotlib.cm as mcm
            rgb = (mcm.get_cmap(cmap)(t)[:, :3] * 255).astype(np.uint8)
        except ImportError:
            g = (t * 255).astype(np.uint8)
            rgb = np.stack([g, g, g], axis=-1)
        _CMAP_CACHE[cmap] = rgb
    return _CMAP_CACHE[cmap]

def _paint_grid_geometry(
    painter: QPainter, grid_data: dict, w: int,
) -> None:
    line_w = scaled_grid_line_width(w)
    for face in ('floor', 'wall_l', 'wall_b'):
        pane = grid_data.get(f'pane_{face}')
        if pane:
            r, g, b = hex_to_rgb(
                _GRID_FACE_COLORS.get(face, GRID_COLOR_FLOOR)
            )
            fill = QColor.fromRgbF(r, g, b)
            fill.setAlphaF(GRID_PANE_ALPHA)
            painter.setBrush(QBrush(fill))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(
                QPolygon([QPoint(x, y) for x, y in pane])
            )
    for face in ('floor', 'wall_l', 'wall_b'):
        lines = grid_data.get(face, [])
        if not lines:
            continue
        r, g, b = hex_to_rgb(
            _GRID_FACE_COLORS.get(face, GRID_COLOR_FLOOR)
        )
        c = QColor.fromRgbF(r, g, b)
        c.setAlphaF(GRID_LINE_ALPHA)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(c, line_w))
        for x1, y1, _z1, x2, y2, _z2 in lines:
            painter.drawLine(x1, y1, x2, y2)

def _paint_grid_labels(painter: QPainter, grid_data: dict) -> None:
    if STARTUP_GRID_TICKS and grid_data.get('ticks'):
        painter.save()
        f = make_font()
        f.setPointSize(8)
        painter.setFont(f)
        painter.setPen(QColor.fromRgbF(*hex_to_rgb(GRID_TICK_COLOR)))
        for x, y, text in grid_data['ticks']:
            painter.drawText(x + 2, y - 2, text)
        painter.restore()
    if STARTUP_GRID_LABELS and grid_data.get('axis_labels'):
        painter.save()
        f = make_font()
        f.setPointSize(11)
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(
            QColor.fromRgbF(*hex_to_rgb(GRID_AXIS_LABEL_COLOR))
        )
        for x, y, text in grid_data['axis_labels']:
            painter.drawText(x, y, text)
        painter.restore()

def paint_grid(painter: QPainter, grid_data: dict, w: int) -> None:
    _paint_grid_geometry(painter, grid_data, w)
    _paint_grid_labels(painter, grid_data)

def paint_bbox(painter: QPainter, bbox_lines: list, w: int) -> None:
    if not bbox_lines:
        return
    c = QColor.fromRgbF(*hex_to_rgb(BBOX_COLOR))
    c.setAlphaF(BBOX_LINE_ALPHA)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(c, scaled_bbox_line_width(w)))
    for x1, y1, _z1, x2, y2, _z2 in bbox_lines:
        painter.drawLine(x1, y1, x2, y2)

def paint_depth_correct_overlays(
    painter: QPainter,
    bbox_lines: list,
    grid_data: dict,
    depth_buffer: np.ndarray,
    w: int,
    h: int,
) -> None:
    all_segs = list(bbox_lines)
    for face in ('floor', 'wall_l', 'wall_b'):
        all_segs.extend(grid_data.get(face, []))
    if not all_segs:
        _paint_grid_labels(painter, grid_data)
        return
    overlay = QImage(w, h, QImage.Format.Format_ARGB32)
    overlay.fill(QColor(0, 0, 0, 0))
    op = QPainter(overlay)
    op.setRenderHint(QPainter.RenderHint.Antialiasing, ANTIALIAS)
    _paint_grid_geometry(op, grid_data, w)
    paint_bbox(op, bbox_lines, w)
    op.end()
    depth_mask = build_depth_mask(all_segs, depth_buffer, h, w)
    bits = overlay.bits()
    arr = np.frombuffer(bits, dtype=np.uint8).reshape(h, w, 4).copy()

    arr[:, :, 3][depth_mask < 0.5] = 0
    masked = QImage(
        arr.data, w, h, w * 4, QImage.Format.Format_ARGB32
    ).copy()
    painter.drawImage(0, 0, masked)
    _paint_grid_labels(painter, grid_data)

def paint_colormap_bar(
    painter: QPainter, info: dict, w: int, h: int,
) -> None:
    cmap = info['cmap']
    l_top, l_bot = info['label_top'], info['label_bot']
    text_clr = info.get('text_clr') or _BAR_TEXT_CLR
    gap = 4
    bar_x = w - 24 - _BAR_W
    bar_y = (h - _BAR_H) // 2
    rgb_2d = np.repeat(
        _get_cmap_gradient(cmap)[:, np.newaxis, :], _BAR_W, axis=1,
    )
    bar_img = QImage(
        rgb_2d.data, _BAR_W, _BAR_H, _BAR_W * 3,
        QImage.Format.Format_RGB888,
    ).copy()
    fm = painter.fontMetrics()
    adv = fm.horizontalAdvance
    cx = bar_x + _BAR_W // 2
    painter.save()
    painter.drawImage(bar_x, bar_y, bar_img)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor.fromRgbF(*hex_to_rgb(CMAP_BAR_BORDER_COLOR)), 1))
    painter.drawRect(bar_x, bar_y, _BAR_W - 1, _BAR_H - 1)
    painter.setPen(QColor.fromRgbF(*text_clr))
    painter.drawText(cx - adv(l_top) // 2, bar_y - gap, l_top)
    painter.drawText(
        cx - adv(l_bot) // 2,
        bar_y + _BAR_H + fm.ascent() + gap, l_bot,
    )
    painter.restore()

def paint_seq_inset(
    painter: QPainter,
    frame: np.ndarray,
    opacity: float,
    w: int,
    h: int,
) -> None:
    if frame is None or opacity <= 0.0:
        return
    fh, fw = frame.shape[:2]
    has_alpha = frame.ndim == 3 and frame.shape[2] == 4
    fmt = (
        QImage.Format.Format_RGBA8888
        if has_alpha else QImage.Format.Format_RGB888
    )
    bpl = fw * (4 if has_alpha else 3)
    inset_w = scaled_seq_inset_w(w)
    inset_margin = scaled_seq_inset_margin(w)
    inset_h = max(1, round(inset_w * fh / fw))
    src = QImage(
        np.ascontiguousarray(frame).data, fw, fh, bpl, fmt
    ).copy()
    scaled = src.scaled(
        inset_w, inset_h,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    sx = w - scaled.width() - inset_margin
    sy = h - scaled.height() - inset_margin
    radius = scaled_seq_inset_radius(w)
    painter.save()
    painter.setOpacity(opacity)
    if radius > 0:

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip = QPainterPath()
        clip.addRoundedRect(
            QRectF(sx, sy, scaled.width(), scaled.height()),
            radius, radius,
        )
        painter.setClipPath(clip)
    painter.drawImage(sx, sy, scaled)
    painter.restore()
