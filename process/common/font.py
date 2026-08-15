from PySide6.QtGui import QFont

from configs.settings_typo import FONT_PRIORITY

def make_font() -> QFont:
    f = QFont()
    f.setFamilies(list(FONT_PRIORITY))
    return f
