import logging

from PySide6.QtCore import QPoint, QRect, QTimer
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QMenu

from configs.settings import MENU_CAPTURE_PUMP_MS

logger = logging.getLogger(__name__)

def _pump_save(window) -> None:
    if getattr(window, '_save_dir', None) is None:
        return
    arr = getattr(getattr(window, '_widget', None), '_image_arr', None)
    if arr is None:
        return
    window._auto_save(arr)

def _clamp_into_render_area(window, menu: QMenu, pos: QPoint) -> QPoint:
    central = window.centralWidget()
    if central is None:
        return pos
    origin = central.mapToGlobal(QPoint(0, 0))
    rect = QRect(origin.x(), origin.y(), central.width(), central.height())
    hint = menu.sizeHint()
    x = min(pos.x(), rect.x() + rect.width() - hint.width())
    y = min(pos.y(), rect.y() + rect.height() - hint.height())
    x = max(x, rect.x())
    y = max(y, rect.y())
    return QPoint(x, y)

def exec_menu_capture(window, menu: QMenu, global_pos) -> QAction | None:
    if getattr(window, '_save_dir', None) is None:

        return menu.exec(_clamp_into_render_area(window, menu, global_pos))

    global_pos = _clamp_into_render_area(window, menu, QCursor.pos())
    timer = QTimer(window)
    timer.setInterval(MENU_CAPTURE_PUMP_MS)
    timer.timeout.connect(lambda: _pump_save(window))
    logger.debug('Menu capture pump started (%d ms)', MENU_CAPTURE_PUMP_MS)
    timer.start()
    try:
        return menu.exec(global_pos)
    finally:
        timer.stop()
        timer.deleteLater()
