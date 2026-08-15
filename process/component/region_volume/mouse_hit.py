from PySide6.QtCore import Qt

from process.component.region_volume.handles import (
    region_volume_world_length, pick_rotate_axis, pick_translate_axis,
)
from process.component.region_volume.hover_select import hover_winner
from process.component.region_volume.picking import ray_aabb, screen_ray
from process.component.region_volume.settings import (
    REGION_VOLUME_ROTATE_TOL_RATIO,
    TOOL_ROTATE, TOOL_SCALE, TOOL_TRANSLATE,
)

class RegionVolumeHitTestMixin:

    def _locked(self) -> bool:
        fn = getattr(self._ctrl, 'is_region_locked', None)
        return bool(fn()) if callable(fn) else False

    def _event_shift(self, event) -> bool:
        return bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )

    def _is_active(self) -> bool:
        if self._locked():
            return False
        return (
            self._ctrl.is_visible()
            and self._ctrl.tool_mode in (
                TOOL_TRANSLATE, TOOL_SCALE, TOOL_ROTATE,
            )
        )

    def _axes(self):
        import numpy as np
        return np.asarray(
            self._ctrl.target.rotation, dtype=np.float32,
        ).T

    def _world_len(self) -> float:
        anchor = self._ctrl.target.center
        return region_volume_world_length(
            self._window, anchor, self._screen_len_px,
        )

    def _is_select_winner(self) -> bool:
        win = self._window
        reg = getattr(win, '_region_volume_registry', None)
        members = getattr(reg, 'members', None)
        if not members or len(members) <= 1:
            return True
        winner = hover_winner(members)
        return winner is None or winner is self._ctrl

    def _pick(self, mx: int, my: int) -> tuple[str, int] | None:
        if not self._is_active():
            return None
        target = self._ctrl.target
        anchor = target.center
        world_len = self._world_len()
        axes = self._axes()
        mode = self._ctrl.tool_mode
        if mode == TOOL_TRANSLATE:
            axis = pick_translate_axis(
                self._window, anchor, axes, world_len,
                mx, my, self._pick_tol_px,
            )
            return ('translate_axis', axis) if axis is not None else None
        if mode == TOOL_SCALE:
            axis = pick_translate_axis(
                self._window, anchor, axes, world_len,
                mx, my, self._pick_tol_px,
            )
            return ('scale_axis', axis) if axis is not None else None
        if mode == TOOL_ROTATE:
            ray = screen_ray(self._window, float(mx), float(my))
            if ray is None:
                return None
            origin, direction = ray
            tol = world_len * REGION_VOLUME_ROTATE_TOL_RATIO
            axis = pick_rotate_axis(
                self._window, anchor, axes, world_len,
                mx, my, tol, origin, direction,
            )
            return ('rotate_axis', axis) if axis is not None else None
        return None

    def _hit_box(self, mx: int, my: int) -> bool:
        target = self._ctrl.target
        if target is None:
            return False
        ray = screen_ray(self._window, float(mx), float(my))
        if ray is None:
            return False
        origin, direction = ray
        ray_hit = getattr(target, 'ray_hit', None)
        if ray_hit is not None:
            return ray_hit(origin, direction) is not None
        corners = target.corners()
        lo = corners.min(axis=0)
        hi = corners.max(axis=0)
        return ray_aabb(origin, direction, lo, hi) is not None
