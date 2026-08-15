import logging

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QKeyEvent, QResizeEvent

from configs.settings_window import SET_WINDOW_FIXED_SIZE
from configs.system_resources import get_system_info, get_gpu_info
from process.keys.dispatch import dispatch
import process.mouse.handler as mouse_handler

logger = logging.getLogger(__name__)

class EventsMixin:

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not SET_WINDOW_FIXED_SIZE:
            return
        if self.size() != QSize(self._disp_w, self._disp_h):
            self.setFixedSize(self._disp_w, self._disp_h)

    def _on_cam_event(self, kind: str, event) -> None:
        for fn in self._mouse_handlers:
            try:
                if fn(kind, event):
                    return
            except Exception:
                logger.exception('Mouse handler error')
        mouse_handler.on_cam_event(self, kind, event)

    def _sys_monitor_loop(self) -> None:
        while not self._stop_sys_event.wait(timeout=1.5):
            self._sys_info = get_system_info(cpu_interval=None)
            if not self._stop_sys_event.is_set():
                self._gpu_info = get_gpu_info()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        dispatch(
            self, event.key(), event.modifiers(),
            auto_repeat=event.isAutoRepeat(),
        )

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return
        qt_key = event.key()
        for key_char, fn in self._extra_release_handlers.items():
            try:
                if getattr(Qt.Key, f'Key_{key_char}') == qt_key:
                    fn(self)
                    return
            except AttributeError:
                continue
