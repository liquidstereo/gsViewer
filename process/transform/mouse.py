import logging

from PySide6.QtCore import Qt

from configs.settings_transform import (
    TOOL_SCALE, TOOL_TRANSLATE, TRANSFORM_CLICK_TOL_PX,
)
from process.common import display_name
from process.handle import overlay_event
from process.transform.attr_overlay import close_attr_editor_panel, deselect_all
from process.transform.controller import InputTransformController
from process.transform.drag import (
    DragState, apply_rotate, apply_scale, apply_translate,
    start_rotate, start_scale, start_translate,
)
from process.transform.free_drag import (
    apply_free_translate, apply_trackball, begin_free_drag,
)
from process.transform.mouse_hit import InputTransformHitTestMixin
from process.undo import record_transform, snapshot_transform

logger = logging.getLogger(__name__)

class InputTransformMouseHandler(InputTransformHitTestMixin):

    def __init__(
        self, window, controller: InputTransformController,
    ) -> None:
        self._window = window
        self._ctrl = controller
        self._drag: DragState | None = None
        self.hover: tuple[str, int] | None = None

        self.shift_active: bool = False
        self._press_pos: tuple[int, int] | None = None
        self._maybe_deselect: bool = False

        self._pending_select: str | None = None
        self._undo_before: tuple[str, dict] | None = None

    def attach(self) -> None:
        handlers = getattr(self._window, '_mouse_handlers', None)
        if handlers is None:
            return
        handlers.append(self.handle)

    def _commit_drag_start(
        self, ds: DragState | None, hover: tuple[str, int] | None,
    ) -> bool:
        if ds is None:
            return False
        target = self._ctrl.target
        self._drag = ds
        close_attr_editor_panel(self._window)
        if self._ctrl.selected_id is not None and target is not None:
            self._undo_before = (
                self._ctrl.selected_id, snapshot_transform(target),
            )
        self.hover = hover
        return True

    def _start(self, kind: str, axis: int, mx: int, my: int) -> bool:
        target = self._ctrl.target
        win = self._window
        if kind == 'translate_axis':
            ds = start_translate(win, target, axis, mx, my)
        elif kind in ('scale_axis', 'uniform_center'):
            ds = start_scale(win, target, kind, axis, mx, my)
        elif kind == 'rotate_axis':
            ds = start_rotate(win, target, axis, mx, my)
        else:
            ds = None
        return self._commit_drag_start(ds, (kind, axis))

    def _start_free(self, mx: int, my: int) -> bool:

        if (not self._on_center(mx, my)
                and self._pick_handle(mx, my) is None
                and not self._hit_target(mx, my)):
            return False
        mode = self._ctrl.tool_mode
        ds = begin_free_drag(self._window, self._ctrl.target, mode, mx, my)
        return self._commit_drag_start(ds, None)

    def _is_click(self, mx: int, my: int) -> bool:
        if self._press_pos is None:
            return False
        dx = mx - self._press_pos[0]
        dy = my - self._press_pos[1]
        return (dx * dx + dy * dy) <= TRANSFORM_CLICK_TOL_PX ** 2

    def _press(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        self._press_pos = (mx, my)
        self._maybe_deselect = False
        self._pending_select = None
        if self._ctrl.target is not None:
            if self._event_shift(event) and self._start_free(mx, my):
                return True
            handle = self._pick_handle(mx, my)
            if handle is not None:
                kind, axis = handle
                return self._start(kind, axis, mx, my)
        picked = self._pick_input(mx, my)
        if picked is None:

            self._maybe_deselect = True
            return False

        self._pending_select = picked
        return False

    def _move_drag(self, event) -> bool:
        ds = self._drag
        if ds is None:
            return False
        target = self._ctrl.target
        if target is None:
            return False
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        win = self._window
        if ds.mode == 'translate':
            apply_translate(win, target, ds, mx, my)
        elif ds.mode == 'free_translate':
            apply_free_translate(win, target, ds, mx, my)
        elif ds.mode in ('scale_axis', 'uniform_center', 'uniform'):
            apply_scale(win, target, ds, mx, my)
        elif ds.mode == 'rotate':
            apply_rotate(win, target, ds, mx, my)
        elif ds.mode == 'trackball':
            apply_trackball(win, target, ds, mx, my)
        self._ctrl.on_change()
        return True

    def _move_hover(self, event) -> bool:
        if self._ctrl.target is None:
            if self.hover is not None or self.shift_active:
                self.hover = None
                self.shift_active = False
                self._ctrl.on_change()
            return False
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        new_hover = self._pick_handle(mx, my)
        shift = self._event_shift(event)
        if new_hover != self.hover or shift != self.shift_active:
            self.hover = new_hover
            self.shift_active = shift
            self._ctrl.on_change()
        return False

    def _log_commit(self) -> None:

        ctrl = self._ctrl
        target = ctrl.get_selected_target()
        if target is None or ctrl.selected_id is None:
            return
        tgt = f'Object({display_name(self._window, ctrl.selected_id)})'
        tool = ctrl.tool_mode
        if tool == TOOL_TRANSLATE:
            v = (target.center - target.pivot).tolist()
            value = '%.3f, %.3f, %.3f' % tuple(v)
            overlay_event(logger, tgt, 'Update', attr='Position',
                          value=value, to_file=True)
        elif tool == TOOL_SCALE:
            base = target.initial_size
            r = [s / b if b else 1.0 for s, b in zip(target.size, base)]
            value = '%.3f, %.3f, %.3f' % tuple(r)
            overlay_event(logger, tgt, 'Update', attr='Scale',
                          value=value, to_file=True)
        else:
            overlay_event(logger, tgt, 'Update', attr='Rotation',
                          to_file=True)

    def _record_undo(self) -> None:
        before = self._undo_before
        self._undo_before = None
        if before is None:
            return
        input_id, snap = before
        target = self._ctrl.targets.get(input_id)
        if target is None:
            return
        record_transform(
            self._window, self._ctrl, input_id, snap,
            snapshot_transform(target),
        )

    def _release(self, event) -> bool:
        if self._drag is not None:
            self._drag = None
            self._ctrl.on_commit()
            self._log_commit()
            self._record_undo()
            return True
        pending = self._pending_select
        self._pending_select = None
        maybe_deselect = self._maybe_deselect
        self._maybe_deselect = False
        if pending is None and not maybe_deselect:
            return False
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        if not self._is_click(mx, my):
            return False
        if pending is not None:
            new_id = None if pending == self._ctrl.selected_id else pending
            self._ctrl.select(new_id)
        else:

            deselect_all(self._window)
        self._ctrl.on_change()
        return False

    def handle(self, kind: str, event) -> bool:
        if kind == 'press':
            return self._press(event)
        if kind == 'release':
            return self._release(event)
        if kind == 'move':
            if self._drag is not None:
                return self._move_drag(event)
            return self._move_hover(event)
        return False
