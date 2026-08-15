from typing import Protocol
import logging

from PySide6.QtCore import Qt

from process.component.region_volume.drag import (
    DragState, apply_free_translate, apply_rotate, apply_scale,
    apply_trackball, apply_translate, start_free_translate, start_rotate,
    start_scale, start_translate, start_trackball,
)
from configs.settings_transform import MAIN_OBJECT_PICK
from process.transform.attr_overlay import (
    close_attr_editor_panel, reset_attr_overlay_if_idle,
)
from process.component.region_volume.mouse_hit import RegionVolumeHitTestMixin
from process.component.region_volume.settings import (
    REGION_VOLUME_CLICK_TOL_PX, REGION_VOLUME_PICK_TOL_PX,
    REGION_VOLUME_SCREEN_LEN_PX, REGION_VOLUME_TOOL_DEFAULT,
    TOOL_NONE, TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
)
from process.component.region_volume.target import TransformTarget
from process.undo import record_region, snapshot_transform

logger = logging.getLogger(__name__)

class RegionVolumeController(Protocol):
    tool_mode: str
    target: TransformTarget

    def is_visible(self) -> bool:
        ...

    def on_change(self) -> None:
        ...

    def on_commit(self) -> None:
        ...

class RegionVolumeMouseHandler(RegionVolumeHitTestMixin):

    def __init__(self, controller: RegionVolumeController) -> None:
        self._ctrl = controller
        self._drag: DragState | None = None
        self.hover: tuple[str, int] | None = None

        self.hover_body: bool = False

        self.hover_hidden: bool = False

        self.shift_active: bool = False
        self._window = None
        self._screen_len_px: float = float(REGION_VOLUME_SCREEN_LEN_PX)
        self._pick_tol_px: float = float(REGION_VOLUME_PICK_TOL_PX)
        self._press_pos: tuple[int, int] | None = None
        self._maybe_deselect: bool = False
        self._undo_before: dict | None = None

    def attach(self, window) -> None:
        self._window = window
        window._mouse_handlers.append(self.handle)

    def is_dragging(self) -> bool:
        return self._drag is not None

    def _select(self) -> None:
        fn = getattr(self._ctrl, 'on_select', None)
        if callable(fn):
            fn()

    def _start(self, kind: str, axis: int, mx: int, my: int) -> bool:
        win = self._window
        target = self._ctrl.target
        if kind == 'translate_axis':
            ds = start_translate(win, target, axis, mx, my)
        elif kind == 'scale_axis':
            ds = start_scale(win, target, kind, axis, mx, my)
        elif kind == 'rotate_axis':
            ds = start_rotate(win, target, axis, mx, my)
        else:
            ds = None
        if ds is None:
            return False
        self._drag = ds
        self._undo_before = snapshot_transform(target)
        self.hover = (kind, axis)
        return True

    def _start_free(self, mx: int, my: int) -> bool:
        if self._pick(mx, my) is None and not self._hit_box(mx, my):
            return False
        win = self._window
        target = self._ctrl.target
        mode = self._ctrl.tool_mode
        if mode == TOOL_TRANSLATE:
            ds = start_free_translate(win, target, mx, my)
        elif mode == TOOL_SCALE:
            ds = start_scale(win, target, 'uniform', 0, mx, my)
        elif mode == TOOL_ROTATE:
            ds = start_trackball(win, target, mx, my)
        else:
            ds = None
        if ds is None:
            return False
        self._drag = ds
        self._undo_before = snapshot_transform(target)
        self.hover = None
        return True

    def _is_click(self, mx: int, my: int) -> bool:
        if self._press_pos is None:
            return False
        dx = mx - self._press_pos[0]
        dy = my - self._press_pos[1]
        return (dx * dx + dy * dy) <= REGION_VOLUME_CLICK_TOL_PX ** 2

    def _maybe_activate(self, mx: int, my: int) -> bool:
        if MAIN_OBJECT_PICK:
            return False
        if self._locked():
            return False
        if not self._ctrl.is_visible():
            return False
        if not self._hit_box(mx, my):
            return False
        if not self._is_select_winner():
            return False
        self._ctrl.tool_mode = REGION_VOLUME_TOOL_DEFAULT
        self._select()
        self._ctrl.on_change()
        return True

    def _press(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        self._press_pos = (mx, my)
        self._maybe_deselect = False
        if not self._is_active():
            if self._maybe_activate(mx, my):
                return True
            reg = getattr(self._window, '_region_volume_registry', None)

            if (self._ctrl.is_visible() and not self._locked()
                    and self._hit_box(mx, my) and self._is_select_winner()):
                if reg is None or not reg.is_active_selection(self._ctrl):
                    self._select()
                    self._ctrl.on_change()
                return True

            if (reg is not None and reg.is_active_selection(self._ctrl)
                    and not self._hit_box(mx, my)):
                self._maybe_deselect = True
            return False
        shift = self._event_shift(event)
        self.shift_active = shift
        if shift and self._start_free(mx, my):
            self._select()
            close_attr_editor_panel(self._window)
            return True
        pick = self._pick(mx, my)
        if pick is None:
            if (not MAIN_OBJECT_PICK and self._hit_box(mx, my)
                    and self._is_select_winner()):
                self._select()
                return True
            self._maybe_deselect = True
            return False
        kind, axis = pick
        if self._start(kind, axis, mx, my):
            self._select()
            close_attr_editor_panel(self._window)
            return True
        return False

    def _move_drag(self, event) -> bool:
        ds = self._drag
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        win = self._window
        target = self._ctrl.target
        if ds.mode == 'translate':
            apply_translate(win, target, ds, mx, my)
        elif ds.mode == 'free_translate':
            apply_free_translate(win, target, ds, mx, my)
        elif ds.mode in ('scale_axis', 'uniform'):
            apply_scale(win, target, ds, mx, my)
        elif ds.mode == 'rotate':
            apply_rotate(win, target, ds, mx, my)
        elif ds.mode == 'trackball':
            apply_trackball(win, target, ds, mx, my)
        self._ctrl.on_change()
        return True

    def _move_hover(self, event) -> bool:
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())

        new_hover = self._pick(mx, my) if self._is_active() else None
        body = (
            self._ctrl.is_visible() and not self._locked()
            and self._hit_box(mx, my)
        )
        hidden = (
            not self._ctrl.is_visible() and self._hit_box(mx, my)
        )
        shift = self._is_active() and self._event_shift(event)
        if (new_hover != self.hover or body != self.hover_body
                or hidden != self.hover_hidden or shift != self.shift_active):
            self.hover = new_hover
            self.hover_body = body
            self.hover_hidden = hidden
            self.shift_active = shift
            self._ctrl.on_change()
        return False

    def _record_undo(self) -> None:
        before = self._undo_before
        self._undo_before = None
        target = self._ctrl.target
        if before is None or target is None:
            return
        record_region(
            self._window, self._ctrl, before, snapshot_transform(target),
        )

    def _release(self, event) -> bool:
        if self._drag is not None:
            self._drag = None
            self._ctrl.on_commit()
            self._record_undo()
            return True
        if not self._maybe_deselect:
            return False
        self._maybe_deselect = False
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        if self._is_click(mx, my):
            self._ctrl.tool_mode = TOOL_NONE

            reg = getattr(self._window, '_region_volume_registry', None)
            if reg is not None:
                reg.user_selected = False
            reset_attr_overlay_if_idle(self._window)
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
