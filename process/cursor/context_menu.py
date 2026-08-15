import logging
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QLabel, QMenu, QWidget, QWidgetAction

from configs.settings_cursor import (
    CONTEXT_MENU_CASCADE_MIN, CONTEXT_MENU_FONT_SIZE,
    CONTEXT_MENU_HEADER_BOLD, CONTEXT_MENU_KIND_SEPARATOR,
    CONTEXT_MENU_OBJECT_FIRST, CONTEXT_MENU_SHOW_OBJECTS,
    CONTEXT_MENU_SHOW_REGIONS, ENABLE_CONTEXT_MENU,
)
from configs.settings_transform import (
    MAIN_OBJECT_PICK, TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
    TRANSFORM_CLICK_TOL_PX, TRANSFORM_KEY_HIDE, TRANSFORM_KEY_LOCK,
    TRANSFORM_KEY_TOOL_ROTATE, TRANSFORM_KEY_TOOL_SCALE,
    TRANSFORM_KEY_TOOL_TRANSLATE,
)
from configs.keybinding import (
    OBJECT_RESET, RESET_ALL, SOLO_TOGGLE, TOGGLE_CORNER_BRACKET,
)
from process.capture.menu_pump import exec_menu_capture
from process.common import display_name
from process.common.qt_signal import connect_triggered
from process.objects.solo import toggle_object_solo
from process.reset.keys import handle_reset_all
from process.transform.picking import ray_aabb, screen_ray
from process.undo import record_object_state, snapshot_object_state

logger = logging.getLogger(__name__)

def _titlecase(text: str) -> str:
    return ' '.join(w.capitalize() for w in text.split(' '))

def _object_items(
    win, ctrl, input_id: str,
) -> list[tuple[str, Callable[[], None]]]:
    def _tool(mode: str) -> None:
        ctrl.select(input_id)
        ctrl.tool_mode = mode
        ctrl.on_change()

    def _lock() -> None:
        before = snapshot_object_state(win, ctrl)
        ctrl.toggle_lock(input_id)
        ctrl.on_change()
        record_object_state(
            win, ctrl, before, snapshot_object_state(win, ctrl), 'Lock',
        )

    def _hide() -> None:
        before = snapshot_object_state(win, ctrl)
        ctrl.toggle_hidden(input_id)
        ctrl.on_change()
        record_object_state(
            win, ctrl, before, snapshot_object_state(win, ctrl), 'Hide',
        )

    def _reset() -> None:
        target = ctrl.targets.get(input_id)
        if target is not None:
            target.reset()
        ctrl.on_change()

    def _toggle_bracket_mode() -> None:
        ctrl.toggle_bracket_mode(input_id)
        ctrl.on_change()

    def _solo() -> None:
        toggle_object_solo(win, input_id)

    lock_label = 'unlock' if ctrl.is_locked(input_id) else 'lock'
    del_label = 'show' if ctrl.is_hidden(input_id) else 'hide'
    solo_label = 'unsolo' if ctrl.solo_id == input_id else 'solo'
    bracket_label = (
        'Display Full' if ctrl.is_bracket_mode(input_id)
        else 'Display as Bracket')

    allow_transform = MAIN_OBJECT_PICK or ctrl.solo_id == input_id
    transform_items = [
        ('translate', lambda: _tool(TOOL_TRANSLATE),
         TRANSFORM_KEY_TOOL_TRANSLATE),
        ('rotate', lambda: _tool(TOOL_ROTATE), TRANSFORM_KEY_TOOL_ROTATE),
        ('scale', lambda: _tool(TOOL_SCALE), TRANSFORM_KEY_TOOL_SCALE),
    ] if allow_transform else []
    return transform_items + [
        (lock_label, _lock, TRANSFORM_KEY_LOCK),
        (del_label, _hide, TRANSFORM_KEY_HIDE),
        (solo_label, _solo, SOLO_TOGGLE),
        (bracket_label, _toggle_bracket_mode, TOGGLE_CORNER_BRACKET),
        ('reset', _reset, OBJECT_RESET),
    ]

def _make_object_provider(window):
    def provider(mx: int, my: int):
        if not MAIN_OBJECT_PICK:
            return None
        ctrl = getattr(window, '_input_transform', None)
        if ctrl is None or not ctrl.targets:
            return None
        ray = screen_ray(window, float(mx), float(my))
        if ray is None:
            return None
        origin, direction = ray
        hits: list[tuple[float, str]] = []
        for input_id, target in ctrl.targets.items():
            corners = target.corners()
            t = ray_aabb(
                origin, direction, corners.min(axis=0), corners.max(axis=0),
            )
            if t is not None:
                hits.append((t, input_id))
        if not hits:
            return None
        hits.sort(key=lambda h: h[0])
        iid = hits[0][1]
        return display_name(window, iid), _object_items(window, ctrl, iid)
    return provider

def _make_object_menu_provider(window):
    def provider() -> list:
        ctrl = getattr(window, '_input_transform', None)
        if ctrl is None or not ctrl.targets:
            return []
        return [
            ('object', display_name(window, iid),
             _object_items(window, ctrl, iid))
            for iid in ctrl.targets
        ]
    return provider

class ContextMenuMouseHandler:

    def __init__(self, window) -> None:
        self._window = window
        self._press_pos: tuple[int, int] | None = None

    def attach(self) -> None:
        handlers = getattr(self._window, '_mouse_handlers', None)
        if handlers is None:
            return
        handlers.append(self.handle)

    def _is_click(self, mx: int, my: int) -> bool:
        if self._press_pos is None:
            return False
        dx = mx - self._press_pos[0]
        dy = my - self._press_pos[1]
        return (dx * dx + dy * dy) <= TRANSFORM_CLICK_TOL_PX ** 2

    def _gather(self) -> list:
        providers = getattr(self._window, '_cursor_menu_targets', ()) or ()
        out: list = []
        for provider in providers:
            try:
                specs = provider()
            except Exception:
                logger.exception('Cursor menu provider error')
                specs = []
            for kind, title, items in specs or ():
                if kind == 'object' and not CONTEXT_MENU_SHOW_OBJECTS:
                    continue
                if kind == 'region' and not CONTEXT_MENU_SHOW_REGIONS:
                    continue
                if items:
                    out.append((kind, title, items))
        return out

    def _apply_font(self, menu: QMenu) -> None:
        if CONTEXT_MENU_FONT_SIZE > 0:
            f = menu.font()
            f.setPointSize(CONTEXT_MENU_FONT_SIZE)
            menu.setFont(f)

    def _add_header(self, menu: QMenu, title: str) -> None:
        label = QLabel(title)
        font = label.font()
        font.setBold(CONTEXT_MENU_HEADER_BOLD)
        if CONTEXT_MENU_FONT_SIZE > 0:
            font.setPointSize(CONTEXT_MENU_FONT_SIZE)
        label.setFont(font)
        label.setContentsMargins(20, 4, 20, 4)
        holder = QWidgetAction(menu)
        holder.setDefaultWidget(label)
        menu.addAction(holder)

    def _add_items(self, menu: QMenu, items: list) -> None:
        for item in items:
            label, action = item[0], item[1]
            key = item[2] if len(item) > 2 else ''
            text = _titlecase(str(label))
            if key:
                text = f'{text}\t{key}'
            act = menu.addAction(text)
            connect_triggered(act, action)

    def _build_flat(self, menu: QMenu, specs: list) -> None:
        for i, (_kind, title, items) in enumerate(specs):
            if i > 0:
                menu.addSeparator()
            self._add_header(menu, _titlecase(str(title)))
            menu.addSeparator()
            self._add_items(menu, items)

    def _build_cascade(self, menu: QMenu, specs: list) -> None:
        prev_kind: str | None = None
        for kind, title, items in specs:
            if (CONTEXT_MENU_KIND_SEPARATOR and prev_kind is not None
                    and kind != prev_kind):
                menu.addSeparator()
            sub = menu.addMenu(_titlecase(str(title)))
            self._apply_font(sub)
            self._add_items(sub, items)
            prev_kind = kind

    def _add_reset_action(self, menu: QMenu) -> None:
        if not menu.isEmpty():
            menu.addSeparator()
        act = menu.addAction(f'{_titlecase("reset all")}\t{RESET_ALL}')
        connect_triggered(act, lambda: handle_reset_all(self._window))

    def _menu_parent(self) -> QWidget | None:
        win = self._window
        return win if isinstance(win, QWidget) else None

    def _show_menu(self) -> bool:
        if not ENABLE_CONTEXT_MENU:
            return False
        specs = self._gather()
        if CONTEXT_MENU_OBJECT_FIRST:
            specs.sort(key=lambda s: 0 if s[0] == 'object' else 1)
        menu = QMenu(self._menu_parent())
        self._apply_font(menu)
        if specs and len(specs) < CONTEXT_MENU_CASCADE_MIN:
            self._build_flat(menu, specs)
        elif specs:
            self._build_cascade(menu, specs)
        self._add_reset_action(menu)
        self._window._drag_pos = None
        self._window._drag_btn = None
        exec_menu_capture(self._window, menu, QCursor.pos())
        return True

    def _press(self, event) -> bool:
        if event.button() != Qt.MouseButton.RightButton:
            return False
        pos = event.position()
        self._press_pos = (int(pos.x()), int(pos.y()))
        return False

    def _release(self, event) -> bool:
        if event.button() != Qt.MouseButton.RightButton:
            return False
        if self._press_pos is None:
            return False
        pos = event.position()
        is_click = self._is_click(int(pos.x()), int(pos.y()))
        self._press_pos = None
        if not is_click:
            return False
        return self._show_menu()

    def handle(self, kind: str, event) -> bool:
        if kind == 'press':
            return self._press(event)
        if kind == 'release':
            return self._release(event)
        return False

def _ensure_targets(window, attr: str) -> list:
    targets = getattr(window, attr, None)
    if targets is None:
        targets = []
        setattr(window, attr, targets)
    return targets

def register_context_menu(window) -> ContextMenuMouseHandler:
    _ensure_targets(window, '_context_menu_targets').append(
        _make_object_provider(window),
    )
    _ensure_targets(window, '_cursor_menu_targets').append(
        _make_object_menu_provider(window),
    )
    handler = ContextMenuMouseHandler(window)
    if ENABLE_CONTEXT_MENU:
        handler.attach()
    logger.info(
        'Context menu registered (enabled=%s)', ENABLE_CONTEXT_MENU,
    )
    return handler
