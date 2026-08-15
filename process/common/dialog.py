from PySide6.QtWidgets import QMessageBox

def confirm(win, title: str, message: str) -> bool:
    reply = QMessageBox.warning(
        win, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes
