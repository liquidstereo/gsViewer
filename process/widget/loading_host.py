import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from configs.settings_overlay import LOADING_OVERLAY_BLINK_PERIOD
from configs.settings_window import ANTIALIAS
from process.widget.paint_loading import paint_loading_overlay
from process.widget.text_case import apply_overlay_case

logger = logging.getLogger(__name__)

_BLINK_TICK_MS: int = max(16, int(LOADING_OVERLAY_BLINK_PERIOD * 500))

class LoadingOverlayHost(QWidget):

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._text: str = ''
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._blink = QTimer(self)
        self._blink.setInterval(_BLINK_TICK_MS)
        self._blink.timeout.connect(self.update)
        self.hide()

    def set_text(self, text: str | None) -> None:
        self._text = text or ''
        if not self._text:
            if self._blink.isActive():
                self._blink.stop()
            self.hide()
            return
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.show()
        self.raise_()
        if LOADING_OVERLAY_BLINK_PERIOD > 0 and not self._blink.isActive():
            self._blink.start()
        self.update()

    def sync_geometry(self) -> None:
        parent = self.parentWidget()
        if parent is not None and self.isVisible():
            self.setGeometry(parent.rect())

    def paintEvent(self, event) -> None:
        if not self._text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, ANTIALIAS)
        painter.setRenderHint(
            QPainter.RenderHint.TextAntialiasing, ANTIALIAS)
        paint_loading_overlay(
            painter, self.width(), self.height(),
            apply_overlay_case(self._text),
        )
        painter.end()
