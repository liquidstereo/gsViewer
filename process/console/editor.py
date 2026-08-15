import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent, QFont, QKeyEvent, QSyntaxHighlighter,
)
from PySide6.QtWidgets import (
    QFileDialog, QMainWindow, QMessageBox, QPlainTextEdit, QStyle, QWidget,
)

from configs.settings_window import (
    CONSOLE_APPLY_DEBOUNCE_MS, CONSOLE_FONT_FAMILY, CONSOLE_TAB_SPACES,
    CONSOLE_WIDTH_PADDING, CONSOLE_WINDOW_COLS, CONSOLE_WINDOW_H,
)
from configs.settings_typo import (
    SCRIPT_CONSOLE_TEXT_BOLD, SCRIPT_CONSOLE_TEXT_ITALIC,
    SCRIPT_CONSOLE_TEXT_SIZE,
)
from process.console.highlighter import JsonHighlighter, PythonHighlighter
from process.console.menu import MenuItem, add_menu
from process.console.persist import ensure_json_suffix
from process.console.theme import apply_console_theme

logger = logging.getLogger(__name__)

class CodeEditorWindow(QMainWindow):

    source_changed = Signal(str, str)
    save_as_requested = Signal(str)
    load_override_requested = Signal(str)

    reset_default_requested = Signal(str)
    reset_user_default_requested = Signal(str)
    set_user_default_requested = Signal(str)
    promote_user_default_requested = Signal(str)

    def __init__(
        self, target_path: str | Path, parent: QWidget | None = None,
        initial_source: str | None = None,
        help_entries: list[tuple[str, Callable[[], None]]] | None = None,
        title_name: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._path: Path = Path(target_path)
        self._title_name: str | None = title_name
        self._help_entries: list[tuple[str, Callable[[], None]]] = (
            help_entries or [])
        self._loading: bool = False
        self._dirty: bool = False
        self._highlighter: QSyntaxHighlighter | None = None
        self._edit: QPlainTextEdit = QPlainTextEdit(self)
        self._apply_timer: QTimer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(CONSOLE_APPLY_DEBOUNCE_MS)
        self._apply_timer.timeout.connect(self._emit_source)
        self._build_editor()
        self._apply_highlighter()
        self.setCentralWidget(self._edit)
        self._build_menu()
        self.setFixedSize(self._fit_width(), CONSOLE_WINDOW_H)
        self._load(self._path, initial_source)
        self._edit.textChanged.connect(self._on_changed)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def _apply_highlighter(self) -> None:

        if self._highlighter is not None:
            self._highlighter.setDocument(None)
        doc = self._edit.document()
        if str(self._path).lower().endswith('.json'):
            self._highlighter = JsonHighlighter(doc)
        else:
            self._highlighter = PythonHighlighter(doc)

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

    def _fit_width(self) -> int:

        char_w = self._edit.fontMetrics().horizontalAdvance('M')
        doc_margin = int(self._edit.document().documentMargin())
        frame = self._edit.frameWidth()
        scrollbar = self.style().pixelMetric(
            QStyle.PixelMetric.PM_ScrollBarExtent)
        return (char_w * CONSOLE_WINDOW_COLS + doc_margin * 2
                + frame * 2 + scrollbar + CONSOLE_WIDTH_PADDING)

    def _build_menu(self) -> None:

        add_menu(self.menuBar(), 'File', self._file_items(), self)
        if self._help_entries:
            add_menu(self.menuBar(), 'Help', self._help_items(), self)

    def _file_items(self) -> list[MenuItem]:

        return [
            MenuItem('Open', self._open, 'Ctrl+O'),
            MenuItem('Apply JSON Settings', self._apply_json,
                     'Ctrl+Shift+A', True),
            MenuItem('Save As', self._save_as, 'Ctrl+S', True),
            MenuItem('Reset to Default', self._reset_default),
            MenuItem('Reset to User Default', self._reset_user_default),
            MenuItem('Set as User Default', self._set_user_default),
            MenuItem('Set User Defaults as Default',
                     self._promote_user_default, '', True),
            MenuItem('Exit', self.close, 'Ctrl+Q'),
        ]

    def _help_items(self) -> list[MenuItem]:

        return [MenuItem(label, slot) for label, slot in self._help_entries]

    def _preset_dir(self) -> Path:
        preset = self._path.parent / 'preset'
        try:
            preset.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning('Preset dir create failed: %s', e)
            return self._path.parent
        return preset

    def refresh_source(self, text: str) -> None:
        self._load(self._path, text)
        self._dirty = False

    def _set_title(self) -> None:
        name = self._title_name
        self.setWindowTitle(
            f'Script Console - {name}' if name else 'Script Console')

    def _load(self, path: str | Path, text: str | None = None) -> None:
        self._loading = True
        if text is None:
            try:
                text = Path(path).read_text(encoding='utf-8')
            except OSError as e:
                logger.warning('Console load failed: %s', e)
                text = ''
        self._edit.setPlainText(text)
        self._loading = False
        self._path = Path(path)
        self._apply_highlighter()
        self._set_title()
        logger.info('Console loaded: %s', self._path.name)

    def _on_changed(self) -> None:
        if self._loading:
            return
        self._dirty = True
        self._apply_timer.start()

    def _emit_source(self) -> None:
        self.source_changed.emit(str(self._path), self._edit.toPlainText())

    def _flush_apply(self) -> None:

        if self._apply_timer.isActive():
            self._apply_timer.stop()
            self._emit_source()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._flush_apply()
        self._dirty = False
        super().closeEvent(event)

    def _open(self) -> None:
        start = str(self._preset_dir())
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open Python / Preset JSON', start,
            'JSON (*.json);;Python (*.py);;All (*)')
        if not path:
            return
        if path.lower().endswith('.json'):
            self.load_override_requested.emit(path)
            return
        self._load(path)
        self._on_changed()

    def _apply_json(self) -> None:
        start = str(self._preset_dir())
        path, _ = QFileDialog.getOpenFileName(
            self, 'Apply JSON Settings', start, 'JSON (*.json);;All (*)')
        if not path:
            return
        self.load_override_requested.emit(path)

    def _save_as(self) -> None:
        base = self._preset_dir() / 'preset.json'
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save Settings As', str(base), 'JSON (*.json)')
        if not path:
            return

        path = ensure_json_suffix(path)
        self._flush_apply()
        self.save_as_requested.emit(path)

    def _confirm(self, title: str, text: str) -> bool:

        result = QMessageBox.question(
            self, title, text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return result == QMessageBox.StandardButton.Yes

    def _reset_default(self) -> None:
        if not self._confirm(
                'Reset to Default',
                'Reset all values to the plugin defaults?'):
            return
        self._flush_apply()
        self.reset_default_requested.emit(str(self._path))

    def _reset_user_default(self) -> None:
        if not self._confirm(
                'Reset to User Default',
                'Reset all values to your saved user defaults?'):
            return
        self._flush_apply()
        self.reset_user_default_requested.emit(str(self._path))

    def _set_user_default(self) -> None:
        self._flush_apply()
        self.set_user_default_requested.emit(str(self._path))

    def _promote_user_default(self) -> None:
        if not self._confirm(
                'Set User Defaults as Default',
                'Overwrite plugin defaults (settings.py) with your '
                'user defaults?'):
            return
        self._flush_apply()
        self.promote_user_default_requested.emit(str(self._path))
