import logging
from collections.abc import Callable

from PySide6.QtCore import QTimer

logger = logging.getLogger(__name__)

class BlinkController:

    def __init__(
        self, parent, interval_ms: int,
        on_change: Callable[[bool], None],
    ) -> None:
        self._on: bool = False
        self._on_change = on_change
        self._timer = QTimer(parent)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)

    @property
    def on(self) -> bool:
        return self._on

    @property
    def active(self) -> bool:
        return self._timer.isActive()

    def start(self, initial_on: bool = True) -> None:
        self._on = initial_on
        self._emit()
        self._timer.start()

    def stop(self, final_on: bool = False) -> None:
        self._timer.stop()
        self._on = final_on
        self._emit()

    def _tick(self) -> None:
        self._on = not self._on
        self._emit()

    def _emit(self) -> None:
        try:
            self._on_change(self._on)
        except Exception:
            logger.exception('Blink on_change callback error')
