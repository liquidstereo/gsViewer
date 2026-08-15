import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import QMainWindow, QPlainTextEdit, QWidget

from configs.settings_window import (
    CONSOLE_FONT_FAMILY, CONSOLE_TAB_SPACES, CONSOLE_WINDOW_COLS,
    CONSOLE_WINDOW_H,
)
from configs.settings_typo import (
    SCRIPT_CONSOLE_TEXT_BOLD, SCRIPT_CONSOLE_TEXT_ITALIC,
    SCRIPT_CONSOLE_TEXT_SIZE,
)
from process.console.theme import apply_console_theme

logger = logging.getLogger(__name__)

def current_plugin_readme(settings_path: str) -> tuple[str, Path] | None:
    plugin_dir = Path(settings_path).parent
    readme = plugin_dir / 'README.txt'
    if not readme.is_file():
        return None
    return plugin_dir.name, readme

class ReadOnlyViewer(QMainWindow):

    def __init__(
        self, title: str, text: str, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._edit: QPlainTextEdit = QPlainTextEdit(self)
        self._edit.setReadOnly(True)
        self._build_editor()
        self.setCentralWidget(self._edit)
        self.setWindowTitle(title)
        self._edit.setPlainText(text)
        char_w = self._edit.fontMetrics().horizontalAdvance('M')
        self.resize(char_w * CONSOLE_WINDOW_COLS, CONSOLE_WINDOW_H)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def _build_editor(self) -> None:
        font = QFont()
        font.setFamilies(list(CONSOLE_FONT_FAMILY))
        font.setPointSize(SCRIPT_CONSOLE_TEXT_SIZE)
        font.setBold(SCRIPT_CONSOLE_TEXT_BOLD)
        font.setItalic(SCRIPT_CONSOLE_TEXT_ITALIC)
        font.setFixedPitch(True)
        self._edit.setFont(font)
        apply_console_theme(self._edit)
        advance = self._edit.fontMetrics().horizontalAdvance(' ')
        self._edit.setTabStopDistance(advance * CONSOLE_TAB_SPACES)

def _read_text(path: Path) -> str:

    try:
        return path.read_text(encoding='utf-8')
    except OSError as e:
        logger.warning('README load failed: %s', e)
        return ''

def show_plugin_readme(window, name: str, path: Path) -> None:
    _show_viewer(window, f'{name} Plugin README', _read_text(path))
    logger.info('Plugin README opened: %s', name)

def show_console_guide(window, text: str, title_name: str = '') -> None:
    title = ('Script Console - How to Use ' + title_name if title_name
             else 'Script Console - Guide')
    _show_viewer(window, title, text)
    logger.info('Script Console guide opened')

def _show_viewer(window, title: str, text: str) -> None:

    existing = getattr(window, '_readme_viewer', None)
    if existing is not None:
        existing.close()
    viewer = ReadOnlyViewer(title, text, parent=window)

    _place_below_console(viewer, window)
    viewer.show()
    _place_below_console(viewer, window)
    QTimer.singleShot(0, lambda: _place_below_console(viewer, window))
    viewer.raise_()
    viewer.activateWindow()
    window._readme_viewer = viewer

def _place_below_console(viewer, window) -> None:
    console = getattr(window, '_script_console', None)
    if console is None:
        return
    cg = console.frameGeometry()
    viewer.move(cg.x(), cg.y() - 50)
