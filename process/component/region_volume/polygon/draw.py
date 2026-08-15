import logging

import numpy as np
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen

from process.common import hex_to_rgb
from process.component.region_volume.key_router import bind_key
from process.component.region_volume.keys import show_message_overlay
from process.component.region_volume.picking import (
    camera_axes, ray_plane_intersect, screen_ray,
)
from process.component.region_volume.registry import get_registry
from process.component.region_volume.settings import VOLUME_SHAPE_POLYGON
from process.component.region_volume.polygon.geometry import polygon_extents
from process.component.region_volume.polygon.settings import (
    POLYGON_DEPTH_MIN, POLYGON_DRAW_LINE_COLOR, POLYGON_DRAW_LINE_WIDTH,
    POLYGON_DRAW_RUBBER_COLOR, POLYGON_DRAW_VERT_COLOR,
    POLYGON_DRAW_VERT_RADIUS, POLYGON_EXTRUDE_INIT_RATIO,
    POLYGON_KEY_COMPLETE, POLYGON_KEY_COMPLETE_KP, POLYGON_KEY_UNDO,
    POLYGON_MIN_VERTS,
)

logger = logging.getLogger(__name__)

class PolygonDrawController:

    def __init__(self, plugin) -> None:
        self.plugin = plugin
        self.points: list[tuple[float, float]] = []
        self.cursor: tuple[float, float] = (0.0, 0.0)
        self._window = None

    def _active(self) -> bool:
        p = self.plugin
        if getattr(p, 'shape', '') != VOLUME_SHAPE_POLYGON:
            return False
        if not p.region_visible:
            return False
        if getattr(p.region, 'committed', True):
            return False
        win = self._window
        if win is not None:
            reg = get_registry(win)
            if reg.count() > 1 and not reg.is_active_selection(p):
                return False
        return True

    def _repaint(self) -> None:
        win = self._window
        widget = getattr(win, '_widget', None)
        if widget is not None:
            widget.update()

    def handle(self, kind: str, event) -> bool:
        if not self._active():
            return False
        pos = event.position()
        mx, my = float(pos.x()), float(pos.y())
        if kind == 'press':
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            self.points.append((mx, my))
            self._repaint()
            return True
        if kind == 'move':
            self.cursor = (mx, my)
            self._repaint()
            return False
        return False

    def complete(self, win) -> None:
        if not self._active():
            return
        if len(self.points) < POLYGON_MIN_VERTS:
            show_message_overlay(win, 'POLYGON: need 3+ points')
            return
        if not self._build(win):
            show_message_overlay(win, 'POLYGON: build failed (face camera)')
            return
        self.points = []
        self.plugin.save_region()
        self.plugin.on_change()
        show_message_overlay(win, 'POLYGON CREATED (R to extrude)')
        logger.info('Polygon region created (%d verts)',
                    len(self.plugin.region.verts2d))

    def undo(self, win) -> None:
        if not self._active() or not self.points:
            return
        self.points.pop()
        self._repaint()

    def _build(self, win) -> bool:
        axes = camera_axes(win)
        if axes is None:
            return False
        right, up, fwd = axes
        anchor = np.asarray(self.plugin.region.center, dtype=np.float32)
        pts3: list[np.ndarray] = []
        for x, y in self.points:
            ray = screen_ray(win, x, y)
            if ray is None:
                return False
            hit = ray_plane_intersect(ray[0], ray[1], anchor, fwd)
            if hit is None:
                return False
            pts3.append(hit)
        arr = np.asarray(pts3, dtype=np.float32)
        centroid = arr.mean(axis=0)
        rel = arr - centroid
        verts2d = np.stack([rel @ right, rel @ up], axis=1).astype(
            np.float32)
        su, sv = polygon_extents(verts2d)
        depth = max(POLYGON_EXTRUDE_INIT_RATIO * max(su, sv),
                    POLYGON_DEPTH_MIN)
        rotation = np.stack([right, up, fwd], axis=1).astype(np.float32)
        center = (centroid + fwd * (depth * 0.5)).astype(np.float32)
        self.plugin.region.set_polygon(verts2d, center, rotation, depth)
        return True

    def paint(
        self, painter: QPainter, w: int, h: int, depth,
    ) -> None:
        if not self._active() or not self.points:
            return
        pts = [QPointF(x, y) for x, y in self.points]
        line = QColor.fromRgbF(*hex_to_rgb(POLYGON_DRAW_LINE_COLOR))
        rubber = QColor.fromRgbF(*hex_to_rgb(POLYGON_DRAW_RUBBER_COLOR))
        vert = QColor.fromRgbF(*hex_to_rgb(POLYGON_DRAW_VERT_COLOR))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(line, POLYGON_DRAW_LINE_WIDTH))
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])
        painter.setPen(QPen(rubber, POLYGON_DRAW_LINE_WIDTH,
                            Qt.PenStyle.DashLine))
        painter.drawLine(pts[-1], QPointF(*self.cursor))
        painter.setPen(QPen(vert, POLYGON_DRAW_LINE_WIDTH))
        painter.setBrush(vert)
        for p in pts:
            painter.drawEllipse(p, POLYGON_DRAW_VERT_RADIUS,
                                POLYGON_DRAW_VERT_RADIUS)

def register_polygon_drawing(window, plugin) -> PolygonDrawController:
    ctrl = PolygonDrawController(plugin)
    ctrl._window = window
    if hasattr(window, '_mouse_handlers'):
        window._mouse_handlers.insert(0, ctrl.handle)
    bind_key(window, plugin, POLYGON_KEY_COMPLETE, ctrl.complete,
             allow_when_hidden=True)
    bind_key(window, plugin, POLYGON_KEY_COMPLETE_KP, ctrl.complete,
             allow_when_hidden=True)
    bind_key(window, plugin, POLYGON_KEY_UNDO, ctrl.undo,
             allow_when_hidden=True)
    if hasattr(window, '_widget'):
        ovs = getattr(window._widget, '_underlay_painters', None)
        if ovs is not None:
            ovs.append(ctrl.paint)
    plugin._polygon_draw = ctrl
    return ctrl
