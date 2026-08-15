from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame, QGraphicsScene, QGraphicsView, QWidget,
)

from configs.settings_window import FORCE_RESIZE_WINDOW, RESIZE_MAX_HEIGHT

def compute_display_scale(h: int) -> float:
    if not FORCE_RESIZE_WINDOW or h <= RESIZE_MAX_HEIGHT:
        return 1.0
    return RESIZE_MAX_HEIGHT / float(h)

def build_central(
    widget: QWidget, w: int, h: int,
) -> tuple[QWidget, int, int]:
    scale = compute_display_scale(h)
    if scale >= 1.0:
        return widget, w, h
    view = QGraphicsView()
    scene = QGraphicsScene(view)

    widget.setParent(None)
    scene.addWidget(widget)
    view.setScene(scene)
    view.setFrameShape(QFrame.Shape.NoFrame)
    view.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    view.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    view.setRenderHint(
        QPainter.RenderHint.SmoothPixmapTransform, True
    )
    view.scale(scale, scale)
    return view, round(w * scale), round(h * scale)
