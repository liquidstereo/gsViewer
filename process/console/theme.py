from PySide6.QtWidgets import QPlainTextEdit

from process.console.settings import CONSOLE_BG_COLOR, CONSOLE_FG_COLOR

def apply_console_theme(edit: QPlainTextEdit) -> None:
    edit.setStyleSheet(
        f'QPlainTextEdit {{ background-color: {CONSOLE_BG_COLOR}; '
        f'color: {CONSOLE_FG_COLOR}; }}')
