from PySide6.QtGui import QColor

from process.common import hex_to_rgb

def qcolor_from_hex(hex_str: str, alpha: int | None = None) -> QColor:
    color = QColor.fromRgbF(*hex_to_rgb(hex_str))
    if alpha is not None:
        color.setAlpha(alpha)
    return color
