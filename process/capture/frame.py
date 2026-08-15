import logging

import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from configs.settings import SAVE_WITH_OVERLAY, SAVE_WITH_POPUP
from process.scroll.overlay_scroll import OverlayScrollArea
from process.widget.paint import begin_overlay

logger = logging.getLogger(__name__)

def grab_frame(window, arr: np.ndarray) -> QImage:
    base = _render_base(window, arr)
    if not SAVE_WITH_POPUP:
        return base
    central = window.centralWidget()
    if central is None:
        return base
    rect = _display_rect(central)
    popups = _overlapping_popups(window, rect)
    if not popups:
        return base
    factor = _render_per_display(base, central)
    return _composite(base, rect.topLeft(), factor, popups)

def grab_frame_for_save(window, arr: np.ndarray) -> QImage:
    w = window._widget
    saved = (w._live_rec_on, w._live_rec_dot, w._message_overlay)
    w._live_rec_on = False
    w._live_rec_dot = False
    rec_msg = getattr(w, '_live_rec_message', None)
    if not SAVE_WITH_OVERLAY or (
            rec_msg is not None and w._message_overlay == rec_msg):
        w._message_overlay = None
    try:
        return grab_frame(window, arr)
    finally:
        (w._live_rec_on, w._live_rec_dot, w._message_overlay) = saved

def _render_base(window, arr: np.ndarray) -> QImage:

    from process.widget.compose import paint_overlay_stack
    h, w, _ = arr.shape
    img = QImage(
        arr.data, w, h, w * 3, QImage.Format.Format_RGB888,
    ).copy()
    widget = window._widget
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    saved_rows = (widget._region_rows, widget._object_rows)
    try:
        begin_overlay(painter)
        paint_overlay_stack(widget, painter, w, h, False, [])
    finally:
        painter.end()
        widget._region_rows, widget._object_rows = saved_rows
    _composite_child_overlays(img, widget)
    return img

def _composite_child_overlays(base: QImage, widget: QWidget) -> None:
    for child in widget.children():
        if not isinstance(child, OverlayScrollArea):
            continue
        if not child.isVisible() or child.width() <= 0 or child.height() <= 0:
            continue
        child.render(base, child.pos())

def _display_rect(central: QWidget) -> QRect:
    origin = central.mapToGlobal(QPoint(0, 0))
    return QRect(origin.x(), origin.y(), central.width(), central.height())

def _overlapping_popups(window, rect: QRect) -> list:
    result = []
    for top in QApplication.topLevelWidgets():
        if top is window or top is window._widget or not top.isVisible():
            continue
        if rect.intersects(top.frameGeometry()):
            result.append(top)
    return result

def _render_per_display(base: QImage, central: QWidget) -> float:
    disp_w = central.width()
    if disp_w <= 0:
        return 1.0
    return base.width() / float(disp_w)

def _composite(
    base: QImage, origin: QPoint, factor: float, popups: list,
) -> QImage:
    canvas = base.copy()
    painter = QPainter(canvas)
    for top in popups:

        tg = top.geometry().topLeft()
        off = QPoint(
            round((tg.x() - origin.x()) * factor),
            round((tg.y() - origin.y()) * factor),
        )
        painter.drawPixmap(off, _scaled_popup(top.grab(), factor))
    painter.end()
    logger.debug(
        'Frame composited with %d popup(s) (factor x%.3f)',
        len(popups), factor,
    )
    return canvas

def _scaled_popup(pix: QPixmap, factor: float) -> QPixmap:
    if factor == 1.0:
        return pix
    return pix.scaled(
        round(pix.width() * factor), round(pix.height() * factor),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
