import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QToolTip

from process.common import request_repaint
from process.handle import overlay_event
from process.widget.overlays.attr_curve_edit import CurveEditMixin
from process.widget.overlays.attr_notice import AttrNoticeMixin
from process.widget.overlays.attr_spec import (
    KIND_BOOL, KIND_BUTTON, KIND_CURVE, KIND_ENUM, KIND_FLOAT, KIND_INT,
)
from process.undo import record_attr
from process.capture.menu_pump import exec_menu_capture

_UNDO_KINDS = (KIND_FLOAT, KIND_INT, KIND_BOOL, KIND_ENUM)

logger = logging.getLogger(__name__)

def _panel_target(row) -> str:
    section = getattr(row, 'section', '') or ''
    return f'Panel({section})' if section else 'Panel'

class AttributeEditorMouseHandler(CurveEditMixin, AttrNoticeMixin):

    def __init__(self, window, surface=None) -> None:
        self._window = window

        self._surface = surface if surface is not None else window._widget
        self._drag = None

        self._curve_idx: int | None = None

        self._commit_before: tuple[str, object] | None = None

    def attach(self) -> None:
        handlers = getattr(self._window, '_mouse_handlers', None)
        if handlers is None:
            return
        handlers.insert(0, self.handle)

    def _rows(self) -> list:
        return getattr(self._surface, '_attr_rows', None) or []

    def _find(self, mx: float, my: float):
        for row in self._rows():
            if row.hit(mx, my):
                return row
        return None

    def _press_row(self, event) -> bool:
        pos = event.position()
        if event.button() == Qt.MouseButton.RightButton:
            row = self._find(pos.x(), pos.y())
            if row is None:
                return False
            if row.role == 'curve_box':
                self._curve_context(row, pos.x(), pos.y())
                return True
            if self._has_context(row):
                self._reset_menu(row, pos)
                return True
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        row = self._find(pos.x(), pos.y())
        if row is None:
            return False
        if row.role == 'curve_header':
            self._toggle_collapse(row.spec)
            return True
        if row.role == 'curve_box':
            self._drag = row
            self._curve_idx = self._curve_pick(row, pos.x(), pos.y())
            if row.spec.get is not None:
                self._commit_before = (
                    row.spec.label,
                    [tuple(p) for p in (row.spec.get() or [])],
                )
            self._curve_apply(row, pos.x(), pos.y())
            return True
        if row.spec.kind == KIND_BUTTON:
            self._surface._attr_pressed_label = row.spec.label
            if row.spec.action is not None:
                row.spec.action()
            overlay_event(logger, _panel_target(row), 'Trigger',
                          attr=row.spec.label, to_file=True)
            request_repaint(self._window)
            return True
        if row.spec.kind == KIND_BOOL:
            if row.spec.set is not None and row.spec.get is not None:
                self._commit_before = (row.spec.label, row.spec.get())
                row.spec.set(not row.spec.get())
                overlay_event(logger, _panel_target(row), 'Update',
                              attr=row.spec.label, value=row.spec.get(),
                              to_file=True)
                request_repaint(self._window)
                self._notify_commit(row)
            return True
        if row.spec.kind == KIND_ENUM:
            self._open_menu(row, pos)
            return True
        self._drag = row
        if row.spec.get is not None:
            self._commit_before = (row.spec.label, row.spec.get())
        self._window._attr_active_edit = (row.section, row.spec.label)
        self._apply(row, pos.x())
        return True

    def _move(self, event) -> bool:
        if self._drag is None:
            return False
        pos = event.position()
        if self._drag.role == 'curve_box':
            self._curve_apply(self._drag, pos.x(), pos.y())
            return True
        self._apply(self._drag, pos.x())
        return True

    def _collapsed_map(self) -> dict:
        surface = self._surface
        cmap = getattr(surface, '_curve_collapsed', None)
        if cmap is None:
            cmap = {}
            surface._curve_collapsed = cmap
        return cmap

    def _toggle_collapse(self, sp) -> None:
        cmap = self._collapsed_map()
        cur = cmap.get(sp.label, sp.collapsed_default)
        cmap[sp.label] = not cur
        request_repaint(self._window)

    def _release(self, event) -> bool:
        cleared = False
        if getattr(self._surface, '_attr_pressed_label', None):
            self._surface._attr_pressed_label = None
            request_repaint(self._window)
            cleared = True
        if self._drag is None:
            return cleared
        row = self._drag
        spec = row.spec
        self._drag = None
        self._curve_idx = None
        self._window._attr_active_edit = None
        text = spec.value_text()
        if text:
            overlay_event(logger, _panel_target(row), 'Update',
                          attr=spec.label, value=text, to_file=True)
        if spec.on_commit is not None:
            spec.on_commit()
        self._notify_commit(row)
        return True

    def _notify_commit(self, row) -> None:
        for cb in getattr(self._window, '_attr_commit_listeners', []):
            cb(row)
        self._push_undo(row)

    def _push_undo(self, row) -> None:
        before = self._commit_before
        self._commit_before = None
        if before is None:
            return
        spec = row.spec
        label, before_val = before
        if spec.label != label or spec.get is None:
            return
        if spec.kind == KIND_CURVE:
            after_val = [tuple(p) for p in (spec.get() or [])]
            record_attr(self._window, self._rows, label, before_val,
                        after_val)
            return
        if spec.kind not in _UNDO_KINDS:
            return
        record_attr(self._window, self._rows, label, before_val, spec.get())

    def _apply(self, row, mx: float) -> None:
        ratio = (mx - row.control_x) / max(1.0, row.control_w)
        row.spec.set_from_norm(ratio)
        self._repaint_live()

    def _repaint_live(self) -> None:
        timer = getattr(self._window, '_timer', None)
        if timer is not None and timer.isActive():
            return
        request_repaint(self._window)

    def _open_menu(self, row, pos) -> None:
        if row.spec.menu_provider is not None:
            self._open_toggle_menu(row, pos)
            return
        widget = self._surface
        menu = QMenu(widget)
        current = str(row.spec.get())
        for opt in row.spec.options:
            act = menu.addAction(str(opt))
            act.setCheckable(True)
            act.setChecked(str(opt) == current)
        gp = widget.mapToGlobal(pos.toPoint())
        chosen = exec_menu_capture(self._window, menu, gp)
        if chosen is not None:
            self._commit_before = (row.spec.label, row.spec.get())
            row.spec.set(chosen.text())
            overlay_event(logger, _panel_target(row), 'Update',
                          attr=row.spec.label, value=chosen.text(),
                          to_file=True)
            request_repaint(self._window)
            self._notify_commit(row)

    def _open_toggle_menu(self, row, pos) -> None:
        widget = self._surface
        menu = QMenu(widget)
        for text, checked in row.spec.menu_provider():
            act = menu.addAction(str(text))
            act.setCheckable(True)
            act.setChecked(bool(checked))
        gp = widget.mapToGlobal(pos.toPoint())
        chosen = exec_menu_capture(self._window, menu, gp)
        if chosen is None:
            return
        row.spec.menu_toggle(chosen.text())
        overlay_event(logger, _panel_target(row), 'Update',
                      attr=row.spec.label, value=chosen.text(),
                      to_file=True)
        request_repaint(self._window)

    def _has_context(self, row) -> bool:
        spec = row.spec
        if spec.menu_provider is not None:
            return False
        if (spec.kind in (KIND_FLOAT, KIND_INT, KIND_ENUM)
                and spec.default is not None):
            return True
        rc = getattr(self._window, '_attr_random', None)
        return rc is not None and spec.kind in (KIND_FLOAT, KIND_ENUM)

    def _reset_menu(self, row, pos) -> None:
        widget = self._surface
        spec = row.spec
        menu = QMenu(widget)
        rc = getattr(self._window, '_attr_random', None)
        rand_act = None
        if rc is not None and spec.kind in (KIND_FLOAT, KIND_ENUM):
            rand_act = menu.addAction('Apply Random')
            rand_act.setCheckable(True)
            rand_act.setChecked(rc.is_active(row.section, spec.label))
        reset_act = (menu.addAction('Reset to default')
                     if spec.default is not None else None)
        if not menu.actions():
            return
        gp = widget.mapToGlobal(pos.toPoint())
        chosen = exec_menu_capture(self._window, menu, gp)
        if chosen is None:
            return
        if chosen is rand_act:
            rc.toggle_target(row.section, spec.label, spec)
            request_repaint(self._window)
            return
        if chosen is reset_act:
            self._do_reset(row)

    def _do_reset(self, row) -> None:
        spec = row.spec
        if spec.set is None:
            return
        if spec.get is not None:
            self._commit_before = (spec.label, spec.get())
        spec.set(spec.default)
        if spec.on_commit is not None:
            spec.on_commit()
        overlay_event(logger, _panel_target(row), 'Reset',
                      attr=spec.label, value=spec.value_text(),
                      to_file=True)
        request_repaint(self._window)
        self._notify_commit(row)

    def handle(self, kind: str, event) -> bool:
        if kind == 'press':
            consumed = self._press_and_notice(event)
        elif kind == 'move':
            if self._drag is None:
                self._hover_tooltip(event)
            consumed = self._move(event)
        elif kind == 'release':
            consumed = self._release(event)
        else:
            return False
        if consumed:
            return True

        if not self._over_panel(event):
            return False
        if kind == 'press':
            return True
        if kind == 'move' and event.buttons() == Qt.MouseButton.NoButton:
            return True
        return False

    def _over_panel(self, event) -> bool:
        rect = getattr(self._surface, '_attr_panel_rect', None)
        if not rect:
            return False
        pos = event.position()
        rx, ry, rw, rh = rect
        return rx <= pos.x() <= rx + rw and ry <= pos.y() <= ry + rh

    def _row_at_y(self, my: float):
        for row in self._rows():
            if row.control_y <= my <= row.control_y + row.control_h:
                return row
        return None

    def _hover_tooltip(self, event) -> None:
        widget = self._surface
        if not self._over_panel(event):
            QToolTip.hideText()
            return
        pos = event.position()
        row = self._find(pos.x(), pos.y()) or self._row_at_y(pos.y())
        tip = getattr(row.spec, 'tooltip', '') if row is not None else ''
        if tip:
            gp = widget.mapToGlobal(event.position().toPoint())
            QToolTip.showText(gp, tip, widget)
        else:
            QToolTip.hideText()

def register_attribute_editor(window):
    from process.scroll.attr_host import register_attr_scroll_host
    return register_attr_scroll_host(window)
