import numpy as np
from PySide6.QtCore import Qt

from configs.settings_transform import (
    MAIN_OBJECT_PICK, TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
    TRANSFORM_PICK_TOL_PX, TRANSFORM_ROTATE_TOL_RATIO,
    TRANSFORM_SCREEN_LEN_PX, TRANSFORM_UNIFORM_TOL_PX,
)
from process.transform.free_drag import hit_target_aabb
from process.overlay_coord import object_gizmo_axes
from process.transform.handles import (
    pick_rotate_axis, pick_translate_axis, pick_uniform_center,
)
from process.transform.picking import (
    ray_aabb, screen_ray, world_length_for_screen_px,
)

class InputTransformHitTestMixin:

    def _event_shift(self, event) -> bool:
        return bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )

    def _axes(self) -> np.ndarray | None:
        target = self._ctrl.target
        if target is None:
            return None
        return object_gizmo_axes(target.rotation)

    def _world_len(self) -> float:
        target = self._ctrl.target
        if target is None:
            return 1.0
        return world_length_for_screen_px(
            self._window, target.center, TRANSFORM_SCREEN_LEN_PX,
        )

    def _on_center(self, mx: int, my: int) -> bool:
        target = self._ctrl.target
        if target is None:
            return False
        return pick_uniform_center(
            self._window, target.center, mx, my, TRANSFORM_UNIFORM_TOL_PX,
        )

    def _hit_target(self, mx: int, my: int) -> bool:
        return hit_target_aabb(self._window, self._ctrl.target, mx, my)

    def _pick_handle(self, mx: int, my: int) -> tuple[str, int] | None:
        target = self._ctrl.target
        if target is None:
            return None
        axes = self._axes()
        if axes is None:
            return None
        anchor = target.center
        world_len = self._world_len()
        mode = self._ctrl.tool_mode
        if mode == TOOL_TRANSLATE:
            axis = pick_translate_axis(
                self._window, anchor, axes, world_len,
                mx, my, TRANSFORM_PICK_TOL_PX,
            )
            return ('translate_axis', axis) if axis is not None else None
        if mode == TOOL_SCALE:
            if pick_uniform_center(
                self._window, anchor, mx, my, TRANSFORM_UNIFORM_TOL_PX,
            ):
                return ('uniform_center', 0)
            axis = pick_translate_axis(
                self._window, anchor, axes, world_len,
                mx, my, TRANSFORM_PICK_TOL_PX,
            )
            return ('scale_axis', axis) if axis is not None else None
        if mode == TOOL_ROTATE:
            ray = screen_ray(self._window, float(mx), float(my))
            if ray is None:
                return None
            origin, direction = ray
            tol = world_len * TRANSFORM_ROTATE_TOL_RATIO
            axis = pick_rotate_axis(
                anchor, axes, world_len, tol, origin, direction,
            )
            return ('rotate_axis', axis) if axis is not None else None
        return None

    def _pick_input(self, mx: int, my: int) -> str | None:
        if not MAIN_OBJECT_PICK and self._ctrl.solo_id is None:
            return None
        ray = screen_ray(self._window, float(mx), float(my))
        if ray is None:
            return None
        origin, direction = ray
        best_id: str | None = None
        best_t = float('inf')
        for input_id, target in self._ctrl.targets.items():
            if self._ctrl.is_locked(input_id):
                continue
            corners = target.corners()
            lo = corners.min(axis=0)
            hi = corners.max(axis=0)
            t = ray_aabb(origin, direction, lo, hi)
            if t is None:
                continue
            if t < best_t:
                best_t = t
                best_id = input_id
        return best_id
