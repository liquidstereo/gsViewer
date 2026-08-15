from typing import Callable, Iterable, NamedTuple

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMenuBar, QWidget

from process.common.qt_signal import connect_triggered

class MenuItem(NamedTuple):

    label: str
    slot: Callable[[], None]
    shortcut: str = ''
    separator: bool = False

def add_menu(
    menubar: QMenuBar, title: str, items: Iterable[MenuItem],
    owner: QWidget,
) -> QMenu:
    remove_menu(menubar, title)
    menu = menubar.addMenu(title)
    for item in items:
        action = QAction(item.label, owner)
        if item.shortcut:
            action.setShortcut(item.shortcut)

        connect_triggered(action, item.slot)
        menu.addAction(action)
        if item.separator:
            menu.addSeparator()
    return menu

def remove_menu(menubar: QMenuBar, title: str) -> bool:
    for action in menubar.actions():
        menu = action.menu()
        if menu is not None and menu.title() == title:
            menubar.removeAction(action)
            return True
    return False
