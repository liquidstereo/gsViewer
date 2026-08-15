import time
from collections.abc import Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QScrollArea, QWidget

SCROLLBAR_WIDTH = 8
SCROLLBAR_HANDLE_MIN_H = 24
SCROLLBAR_HANDLE_RADIUS = 4

SCROLLBAR_HANDLE_COLOR = 'rgba(200, 200, 200, 215)'
SCROLLBAR_HANDLE_HOVER_COLOR = 'rgba(235, 235, 235, 245)'

SCROLLBAR_GAP = 6

_SCROLLBAR_QSS = '''
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent;
    width: {width}px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {handle};
    border-radius: {radius}px;
    min-height: {min_h}px;
}}
QScrollBar::handle:vertical:hover {{ background: {handle_hover}; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px; width: 0px; background: none; border: none;
}}
QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical {{ background: none; border: none; }}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ background: transparent; }}
'''

def _scrollbar_qss() -> str:
    return _SCROLLBAR_QSS.format(
        width=SCROLLBAR_WIDTH,
        handle=SCROLLBAR_HANDLE_COLOR,
        handle_hover=SCROLLBAR_HANDLE_HOVER_COLOR,
        radius=SCROLLBAR_HANDLE_RADIUS,
        min_h=SCROLLBAR_HANDLE_MIN_H,
    )

CHILD_PAINT: list = [0, 0.0]

class OverlayContent(QWidget):

    def __init__(
        self,
        paint_cb: Callable,
        mouse_cb: Callable | None = None,
        parent: QWidget | None = None,
        translucent: bool = True,
    ) -> None:
        super().__init__(parent)
        self._paint_cb = paint_cb
        self._mouse_cb = mouse_cb
        self._content_w: int = 0
        self._content_h: int = 0

        if translucent:
            self.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            self.setStyleSheet('background: transparent;')
        self.setMouseTracking(True)

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_content_size(self, w: float, h: float) -> None:
        w, h = int(w), int(h)
        if (w, h) == (self._content_w, self._content_h):
            return
        self._content_w, self._content_h = w, h
        self.setMinimumHeight(h)
        self.updateGeometry()

    def minimumSizeHint(self) -> QSize:
        return QSize(self._content_w, self._content_h)

    def sizeHint(self) -> QSize:
        return QSize(self._content_w, self._content_h)

    def paintEvent(self, event) -> None:

        _t0 = time.perf_counter()
        painter = QPainter(self)
        try:
            self._paint_cb(painter, self.width(), self.height())
        finally:
            painter.end()
        CHILD_PAINT[0] += 1
        CHILD_PAINT[1] += (time.perf_counter() - _t0) * 1000.0

    def _dispatch_mouse(self, kind: str, event) -> None:
        if self._mouse_cb is not None:
            self._mouse_cb(kind, event)

    def mousePressEvent(self, event) -> None:
        self._dispatch_mouse('press', event)

    def mouseMoveEvent(self, event) -> None:
        self._dispatch_mouse('move', event)

    def mouseReleaseEvent(self, event) -> None:
        self._dispatch_mouse('release', event)

class OverlayScrollArea(QScrollArea):

    def __init__(
        self,
        paint_cb: Callable,
        mouse_cb: Callable | None = None,
        parent: QWidget | None = None,
        translucent: bool = True,
    ) -> None:
        super().__init__(parent)
        self._content = OverlayContent(
            paint_cb, mouse_cb, self, translucent=translucent)
        self.setWidget(self._content)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.viewport().setAutoFillBackground(False)
        if translucent:
            self.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(_scrollbar_qss())

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def wheelEvent(self, event) -> None:
        super().wheelEvent(event)
        event.accept()

    @property
    def content(self) -> OverlayContent:
        return self._content

    def set_content_size(self, w: float, h: float) -> None:
        self._content.set_content_size(w, h)

    def scroll_offset(self) -> int:
        return self.verticalScrollBar().value()
