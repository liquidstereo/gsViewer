from dataclasses import dataclass, replace
import logging

import numpy as np
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QImage, QPainter, QPen, QPolygonF,
)

from process.common import build_depth_mask, hex_to_rgb
from process.keys.bbox_grid import _project_segments
from process.component.region_volume.picking import project_point
from process.component.region_volume.settings import (
    REGION_COLOR, REGION_CORNER_DRAW_PX,
    REGION_FACE_ALPHA, REGION_FACE_ALPHA_SELECTED,
    REGION_FILL_ON_SELECT_ONLY,
    REGION_HOVER_COLOR, REGION_HOVER_LINE_WIDTH,
    REGION_LINE_ALPHA, REGION_LINE_WIDTH, REGION_VOLUME_LOCK_COLOR,
)

logger = logging.getLogger(__name__)

@dataclass
class RegionPalette:
    color: str = REGION_COLOR
    line_alpha: float = REGION_LINE_ALPHA
    line_width: int = REGION_LINE_WIDTH
    hover_line_width: int = REGION_HOVER_LINE_WIDTH
    hover_color: str = REGION_HOVER_COLOR
    corner_draw_px: int = REGION_CORNER_DRAW_PX
    face_alpha: float = REGION_FACE_ALPHA
    face_alpha_selected: float = REGION_FACE_ALPHA_SELECTED

_DEFAULT_PALETTE: RegionPalette = RegionPalette()

def resolve_palette(
    palette: RegionPalette | None,
    locked: bool = False, selected: bool = False,
) -> RegionPalette | None:
    if locked:
        base = palette or _DEFAULT_PALETTE
        return replace(
            base,
            color=REGION_VOLUME_LOCK_COLOR,
            hover_color=REGION_VOLUME_LOCK_COLOR,
        )
    if selected:
        base = palette or _DEFAULT_PALETTE
        return replace(base, color=base.hover_color)
    return palette

def locked_palette(
    palette: RegionPalette | None, locked: bool,
) -> RegionPalette | None:
    return resolve_palette(palette, locked=locked)

def _convex_hull(
    points: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def _cross(o, a, b) -> int:
        return ((a[0] - o[0]) * (b[1] - o[1])
                - (a[1] - o[1]) * (b[0] - o[0]))

    lower: list[tuple[int, int]] = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[int, int]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]

def paint_region_hull(
    painter: QPainter, segs: list,
    palette: RegionPalette | None = None,
    selected: bool = False,
) -> None:
    if not segs:
        return

    if REGION_FILL_ON_SELECT_ONLY and not selected:
        return
    pts: list[tuple[int, int]] = []
    for x1, y1, _z1, x2, y2, _z2 in segs:
        pts.append((int(x1), int(y1)))
        pts.append((int(x2), int(y2)))
    hull = _convex_hull(pts)
    if len(hull) < 3:
        return
    p = palette or _DEFAULT_PALETTE
    alpha = p.face_alpha_selected if selected else p.face_alpha
    qcolor = QColor.fromRgbF(*hex_to_rgb(p.color))
    qcolor.setAlphaF(alpha)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(qcolor))
    painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in hull]))

_FACE_INDICES: tuple[tuple[int, int, int, int], ...] = (
    (0, 1, 2, 3), (4, 5, 6, 7),
    (0, 1, 5, 4), (3, 2, 6, 7),
    (0, 4, 7, 3), (1, 2, 6, 5),
)

_FACE_CORNERS: dict[tuple[int, int], tuple[int, int, int, int]] = {
    (0, +1): (1, 2, 6, 5),
    (0, -1): (0, 3, 7, 4),
    (1, +1): (2, 3, 7, 6),
    (1, -1): (0, 1, 5, 4),
    (2, +1): (4, 5, 6, 7),
    (2, -1): (0, 1, 2, 3),
}

def _get_view_mats(win) -> tuple[np.ndarray, np.ndarray] | None:
    viewmat = getattr(win, '_viewmat', None)
    K = getattr(win, '_K', None)
    if viewmat is None or K is None:
        return None
    return viewmat[0].cpu().numpy(), K[0].cpu().numpy()

def _is_ortho(win) -> bool:
    return getattr(win, '_camera_model', 'pinhole') == 'ortho'

def compute_region_segments(win, region) -> list:
    mats = _get_view_mats(win)
    if mats is None:
        return []
    vm, K_np = mats
    return _project_segments(region.edges(), vm, K_np, _is_ortho(win))

def _project_corners(
    win, corners: np.ndarray,
) -> list[tuple[int, int, float] | None]:
    mats = _get_view_mats(win)
    if mats is None:
        return [None] * len(corners)
    vm, K_np = mats
    is_ortho_v = _is_ortho(win)
    out: list[tuple[int, int, float] | None] = []
    for p in corners:
        c = vm @ np.append(p.astype(np.float32), 1.0)
        if c[2] <= 0:
            out.append(None)
            continue
        if is_ortho_v:
            sx = K_np[0, 0] * c[0] + K_np[0, 2]
            sy = K_np[1, 1] * c[1] + K_np[1, 2]
        else:
            sx = K_np[0, 0] * c[0] / c[2] + K_np[0, 2]
            sy = K_np[1, 1] * c[1] / c[2] + K_np[1, 2]
        out.append((int(sx), int(sy), float(c[2])))
    return out

def _face_edge_segments(
    win, region, axis: int, sign: int,
) -> list:
    corners = region.corners()
    idx = _FACE_CORNERS.get((axis, sign))
    if idx is None:
        return []
    mats = _get_view_mats(win)
    if mats is None:
        return []
    vm, K_np = mats
    pts = [corners[i] for i in idx]
    pairs = [
        (pts[0], pts[1]), (pts[1], pts[2]),
        (pts[2], pts[3]), (pts[3], pts[0]),
    ]
    return _project_segments(pairs, vm, K_np, _is_ortho(win))

def paint_region_faces(
    painter: QPainter, win, region,
    selected: bool = False,
    palette: RegionPalette | None = None,
) -> None:

    if REGION_FILL_ON_SELECT_ONLY and not selected:
        return
    p = palette or _DEFAULT_PALETTE
    proj = _project_corners(win, region.corners())
    alpha = p.face_alpha_selected if selected else p.face_alpha
    qcolor = QColor.fromRgbF(*hex_to_rgb(p.color))
    qcolor.setAlphaF(alpha)
    face_order: list[tuple[float, list[QPointF]]] = []
    for idxs in _FACE_INDICES:
        pts = [proj[i] for i in idxs]
        if any(q is None for q in pts):
            continue
        z = sum(q[2] for q in pts) / 4.0
        poly_pts = [QPointF(float(q[0]), float(q[1])) for q in pts]
        face_order.append((z, poly_pts))
    face_order.sort(key=lambda x: -x[0])
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(qcolor))

    _aa = painter.testRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    for _z, poly_pts in face_order:
        painter.drawPolygon(QPolygonF(poly_pts))
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, _aa)

def _draw_lines(
    painter: QPainter, segs: list, color: QColor, width: int,
) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(color, width))
    for x1, y1, _z1, x2, y2, _z2 in segs:
        painter.drawLine(x1, y1, x2, y2)

def _draw_corner(
    painter: QPainter, win, region, corner_idx: int,
    color: QColor, radius: int,
) -> None:
    corners = region.corners()
    if not (0 <= corner_idx < len(corners)):
        return
    pt = project_point(win, corners[corner_idx])
    if pt is None:
        return
    sx, sy, _ = pt
    painter.setPen(QPen(color, 2))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(QPoint(sx, sy), radius, radius)

def paint_region(
    painter: QPainter, segs: list, depth: np.ndarray | None,
    w: int, h: int, win=None, region=None,
    hover: tuple[str, int, int] | None = None,
    bold: bool = False,
    palette: RegionPalette | None = None,
) -> None:
    if not segs:
        return
    p = palette or _DEFAULT_PALETTE
    base = QColor.fromRgbF(*hex_to_rgb(p.color))
    base.setAlphaF(p.line_alpha)
    line_width = p.hover_line_width if bold else p.line_width
    hi_col = QColor.fromRgbF(*hex_to_rgb(p.hover_color))
    hi_col.setAlphaF(p.line_alpha)
    hi_segs: list = []
    hi_corner: int | None = None
    if hover is not None and win is not None and region is not None:
        kind, a, b = hover
        if kind == 'face':
            hi_segs = _face_edge_segments(win, region, a, b)
        elif kind == 'corner':
            hi_corner = a
    if depth is None:

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        _draw_lines(painter, segs, base, line_width)
        if hi_segs:
            _draw_lines(painter, hi_segs, hi_col, p.hover_line_width)
        if hi_corner is not None:
            _draw_corner(
                painter, win, region, hi_corner, hi_col, p.corner_draw_px,
            )
        painter.restore()
        return
    overlay = QImage(w, h, QImage.Format.Format_ARGB32)
    overlay.fill(QColor(0, 0, 0, 0))
    op = QPainter(overlay)
    op.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _draw_lines(op, segs, base, line_width)
    if hi_segs:
        _draw_lines(op, hi_segs, hi_col, p.hover_line_width)
    if hi_corner is not None:
        _draw_corner(op, win, region, hi_corner, hi_col, p.corner_draw_px)
    op.end()
    mask = build_depth_mask(segs, depth, h, w)
    bits = overlay.bits()
    arr = np.frombuffer(bits, dtype=np.uint8).reshape(h, w, 4).copy()
    alpha = arr[:, :, 3].astype(np.float32) / 255.0 * mask
    arr[:, :, 3] = (alpha * 255.0).clip(0, 255).astype(np.uint8)
    masked = QImage(
        arr.data, w, h, w * 4, QImage.Format.Format_ARGB32,
    ).copy()
    painter.drawImage(0, 0, masked)
