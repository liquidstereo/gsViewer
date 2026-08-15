import logging

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from configs.settings_style import (
    SELECTED_COLOR, SELECTED_LINE_WIDTH, SELECTION_CORNER_RATIO,
)
from configs.settings_transform import (
    TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
    TRANSFORM_AXIS_COLOR_X, TRANSFORM_AXIS_COLOR_Y,
    TRANSFORM_AXIS_COLOR_Z,
    TRANSFORM_HEAD_HEIGHT_RATIO, TRANSFORM_HEAD_WIDTH_RATIO,
    TRANSFORM_CENTER_BRUSH_ALPHA, TRANSFORM_CENTER_BRUSH_COLOR,
    TRANSFORM_CENTER_HOVER_BRUSH_ALPHA, TRANSFORM_CENTER_HOVER_PEN_ALPHA,
    TRANSFORM_CENTER_HOVER_PEN_WIDTH,
    TRANSFORM_CENTER_PEN_ALPHA, TRANSFORM_CENTER_PEN_COLOR,
    TRANSFORM_CENTER_PEN_WIDTH,
    TRANSFORM_HOVER_COLOR,
    TRANSFORM_HOVER_LINE_WIDTH, TRANSFORM_LINE_WIDTH,
    TRANSFORM_SCALE_CENTER_BOX_PX, TRANSFORM_SCALE_HANDLE_SIZE_PX,
)
from process.transform.picking import project_point
from process.common.axis_arrow import filled_arrowhead_poly
from process.widget.scale import scaled_axis_cone_size

logger = logging.getLogger(__name__)

_AXIS_COLORS: tuple[str, str, str] = (
    TRANSFORM_AXIS_COLOR_X, TRANSFORM_AXIS_COLOR_Y, TRANSFORM_AXIS_COLOR_Z,
)

def _hex_to_rgbf(h: str) -> tuple[float, float, float]:
    h = h.lstrip('#')
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )

def _axis_qcolor(axis: int, hovered: bool) -> QColor:
    if hovered:
        hex_str = TRANSFORM_HOVER_COLOR
    else:
        hex_str = _AXIS_COLORS[axis]
    return QColor.fromRgbF(*_hex_to_rgbf(hex_str))

def paint_translate(
    painter: QPainter, win,
    anchor: np.ndarray, axes: np.ndarray, world_len: float,
    hover_axis: int | None, w: int,
) -> None:
    origin_scr = project_point(win, anchor.astype(np.float32))
    if origin_scr is None:
        return
    ox, oy, _ = origin_scr
    cone = scaled_axis_cone_size(w)
    head_len = cone * TRANSFORM_HEAD_HEIGHT_RATIO
    head_half = cone * TRANSFORM_HEAD_WIDTH_RATIO
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for axis in range(3):
        tip = anchor.astype(np.float32) + axes[axis].astype(np.float32) * world_len
        tip_scr = project_point(win, tip)
        if tip_scr is None:
            continue
        tx, ty, _ = tip_scr
        is_hover = hover_axis == axis
        color = _axis_qcolor(axis, is_hover)
        width = (
            TRANSFORM_HOVER_LINE_WIDTH if is_hover else TRANSFORM_LINE_WIDTH
        )
        bx, by, head = filled_arrowhead_poly(
            ox, oy, tx, ty, head_len, head_half,
        )
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(ox, oy, bx, by)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(head)
    painter.restore()

def paint_rotate(
    painter: QPainter, win,
    anchor: np.ndarray, axes: np.ndarray, world_len: float,
    hover_axis: int | None,
) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    segs = 48
    angles = np.linspace(0.0, 2.0 * np.pi, segs, endpoint=False)
    for axis in range(3):
        n = axes[axis].astype(np.float32)
        u = axes[(axis + 1) % 3].astype(np.float32)
        v = axes[(axis + 2) % 3].astype(np.float32)
        is_hover = hover_axis == axis
        color = _axis_qcolor(axis, is_hover)
        width = (
            TRANSFORM_HOVER_LINE_WIDTH if is_hover else TRANSFORM_LINE_WIDTH
        )
        painter.setPen(QPen(color, width))
        last_scr: tuple[int, int] | None = None
        first_scr: tuple[int, int] | None = None
        for a in angles:
            p3 = anchor.astype(np.float32) + (
                u * np.cos(a) + v * np.sin(a)
            ) * world_len
            scr = project_point(win, p3)
            if scr is None:
                last_scr = None
                continue
            sx, sy, _ = scr
            if first_scr is None:
                first_scr = (sx, sy)
            if last_scr is not None:
                painter.drawLine(last_scr[0], last_scr[1], sx, sy)
            last_scr = (sx, sy)
        if last_scr is not None and first_scr is not None:
            painter.drawLine(
                last_scr[0], last_scr[1], first_scr[0], first_scr[1],
            )
        del n
    painter.restore()

def paint_scale(
    painter: QPainter, win,
    anchor: np.ndarray, axes: np.ndarray, world_len: float,
    hover_axis: int | None, hover_uniform: bool,
) -> None:
    origin_scr = project_point(win, anchor.astype(np.float32))
    if origin_scr is None:
        return
    ox, oy, _ = origin_scr
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    for axis in range(3):
        tip = anchor.astype(np.float32) + axes[axis].astype(np.float32) * world_len
        tip_scr = project_point(win, tip)
        if tip_scr is None:
            continue
        tx, ty, _ = tip_scr
        is_hover = hover_axis == axis
        color = _axis_qcolor(axis, is_hover)
        width = (
            TRANSFORM_HOVER_LINE_WIDTH if is_hover else TRANSFORM_LINE_WIDTH
        )
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(ox, oy, tx, ty)
        painter.setBrush(QBrush(color))
        h = TRANSFORM_SCALE_HANDLE_SIZE_PX // 2
        painter.drawRect(tx - h, ty - h, h * 2, h * 2)
    if hover_uniform:
        hov = QColor.fromRgbF(*_hex_to_rgbf(TRANSFORM_HOVER_COLOR))
        pen_col = QColor(hov.red(), hov.green(), hov.blue(),
                         TRANSFORM_CENTER_HOVER_PEN_ALPHA)
        brush_col = QColor(hov.red(), hov.green(), hov.blue(),
                           TRANSFORM_CENTER_HOVER_BRUSH_ALPHA)
        painter.setPen(QPen(pen_col, TRANSFORM_CENTER_HOVER_PEN_WIDTH))
        painter.setBrush(QBrush(brush_col))
    else:
        pen_col = QColor.fromRgbF(*_hex_to_rgbf(TRANSFORM_CENTER_PEN_COLOR))
        pen_col.setAlpha(TRANSFORM_CENTER_PEN_ALPHA)
        brush_col = QColor.fromRgbF(
            *_hex_to_rgbf(TRANSFORM_CENTER_BRUSH_COLOR))
        brush_col.setAlpha(TRANSFORM_CENTER_BRUSH_ALPHA)
        painter.setPen(QPen(pen_col, TRANSFORM_CENTER_PEN_WIDTH))
        painter.setBrush(QBrush(brush_col))
    h = TRANSFORM_SCALE_CENTER_BOX_PX // 2
    painter.drawRect(ox - h, oy - h, h * 2, h * 2)
    painter.restore()

def paint_shift_indicator(
    painter: QPainter, win, anchor: np.ndarray,
) -> None:
    scr = project_point(win, anchor.astype(np.float32))
    if scr is None:
        return
    ox, oy, _ = scr
    hov = QColor.fromRgbF(*_hex_to_rgbf(TRANSFORM_HOVER_COLOR))
    pen_col = QColor(hov.red(), hov.green(), hov.blue(),
                     TRANSFORM_CENTER_HOVER_PEN_ALPHA)
    brush_col = QColor(hov.red(), hov.green(), hov.blue(),
                       TRANSFORM_CENTER_HOVER_BRUSH_ALPHA)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(pen_col, TRANSFORM_CENTER_HOVER_PEN_WIDTH))
    painter.setBrush(QBrush(brush_col))
    h = TRANSFORM_SCALE_CENTER_BOX_PX // 2
    painter.drawRect(ox - h, oy - h, h * 2, h * 2)
    painter.restore()

_TOOL_PAINTERS: dict[str, callable] = {
    TOOL_ROTATE: paint_rotate,
}

def paint_handles(
    painter: QPainter, win, tool_mode: str,
    anchor: np.ndarray, axes: np.ndarray, world_len: float,
    hover_axis: int | None, hover_uniform: bool, w: int,
) -> None:
    if tool_mode == TOOL_TRANSLATE:
        paint_translate(painter, win, anchor, axes, world_len, hover_axis, w)
        return
    if tool_mode == TOOL_SCALE:
        paint_scale(
            painter, win, anchor, axes, world_len,
            hover_axis, hover_uniform,
        )
        return
    fn = _TOOL_PAINTERS.get(tool_mode)
    if fn is None:
        return
    fn(painter, win, anchor, axes, world_len, hover_axis)

def paint_selection_box(
    painter: QPainter, win, edges: list[tuple[np.ndarray, np.ndarray]],
    color_hex: str = SELECTED_COLOR,
    line_width: int = SELECTED_LINE_WIDTH,
    alpha: float = 1.0,
) -> None:
    color = QColor.fromRgbF(*_hex_to_rgbf(color_hex))
    color.setAlphaF(alpha)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(color, line_width))
    ratio = SELECTION_CORNER_RATIO
    for p1, p2 in edges:
        a = p1.astype(np.float32)
        b = p2.astype(np.float32)
        seg = (b - a) * ratio
        for start, stop in ((a, a + seg), (b, b - seg)):
            s1 = project_point(win, start)
            s2 = project_point(win, stop)
            if s1 is None or s2 is None:
                continue
            painter.drawLine(s1[0], s1[1], s2[0], s2[1])
    painter.restore()
