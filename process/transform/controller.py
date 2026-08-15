import logging

import numpy as np
import torch

from configs.settings_transform import (
    MAIN_OBJECT_DISPLAY, MAIN_OBJECT_LOCK, TOOL_NONE,
)
from process.common import display_name
from process.handle import overlay_event, set_message_overlay
from process.widget.text_case import keep_case
from process.transform.attr_overlay import reset_attr_overlay_if_idle
from process.transform.target import InputTransformTarget, aabb_from_means

logger = logging.getLogger(__name__)

class InputTransformController:

    def __init__(self, window) -> None:
        self._window = window
        self.targets: dict[str, InputTransformTarget] = {}
        self.selected_id: str | None = None
        self.locked: set[str] = set()
        self._last_locked: str | None = None
        self.hidden: set[str] = set()
        self._last_hidden: str | None = None

        self.isolate_hidden: set[str] = set()

        self.solo_id: str | None = None

        self.solo_owner_name: str | None = None

        self.bracket_mode: set[str] = set()
        self.point_scale: dict[str, float] = {}
        self.tool_mode: str = TOOL_NONE

        self.attrs_path = None
        self._saved_attrs: dict = {}

    def get_point_scale(self, input_id: str) -> float:
        return float(self.point_scale.get(input_id, 1.0))

    def set_point_scale(self, input_id: str, value: float) -> None:
        self.point_scale[input_id] = float(value)

    def is_hidden(self, input_id: str) -> bool:
        return input_id in self.hidden or input_id in self.isolate_hidden

    def toggle_hidden(self, input_id: str) -> bool:
        tgt = f'Object({display_name(self._window, input_id)})'
        if input_id in self.hidden:
            self.hidden.discard(input_id)
            if self._last_hidden == input_id:
                self._last_hidden = None
            overlay_event(logger, tgt, 'Show', to_file=True)
            return False
        self.hidden.add(input_id)
        self._last_hidden = input_id
        if self.selected_id == input_id:
            self.selected_id = None
        overlay_event(logger, tgt, 'Hide', to_file=True)
        return True

    def unhide_last(self) -> str | None:
        if not self.hidden:
            return None
        target_id = self._last_hidden
        if target_id is None or target_id not in self.hidden:
            target_id = next(iter(self.hidden))
        self.toggle_hidden(target_id)
        return target_id

    def is_bracket_mode(self, input_id: str) -> bool:
        return input_id in self.bracket_mode

    def toggle_bracket_mode(self, input_id: str) -> bool:
        tgt = f'Object({display_name(self._window, input_id)})'
        if input_id in self.bracket_mode:
            self.bracket_mode.discard(input_id)
            overlay_event(logger, tgt, 'Display Full', to_file=True)
            return False
        self.bracket_mode.add(input_id)
        overlay_event(logger, tgt, 'Display as Corner Bracket', to_file=True)
        return True

    def is_locked(self, input_id: str) -> bool:
        return input_id in self.locked

    def toggle_lock(self, input_id: str) -> bool:
        name = display_name(self._window, input_id)
        tgt = f'Object({name})'
        if input_id in self.locked:
            self.locked.discard(input_id)
            if self._last_locked == input_id:
                self._last_locked = None
            overlay_event(logger, tgt, 'Unlock', to_file=True)
            set_message_overlay(
                self._window, f'{keep_case(name)} UNLOCKED')
            return False
        self.locked.add(input_id)
        self._last_locked = input_id
        if self.selected_id == input_id:
            self.selected_id = None
        overlay_event(logger, tgt, 'Lock', to_file=True)
        set_message_overlay(self._window, f'{keep_case(name)} LOCKED')
        return True

    def unlock_last(self) -> str | None:
        if not self.locked:
            return None
        target_id = self._last_locked
        if target_id is None or target_id not in self.locked:
            target_id = next(iter(self.locked))
        self.toggle_lock(target_id)
        return target_id

    def ensure_target(
        self, input_id: str, means: torch.Tensor | np.ndarray,
    ) -> InputTransformTarget | None:
        cached = self.targets.get(input_id)
        if cached is not None:
            return cached
        if isinstance(means, torch.Tensor):
            arr = means.detach().cpu().numpy()
        else:
            arr = np.asarray(means)
        if arr.size == 0:
            return None
        lo, hi = aabb_from_means(arr)
        target = InputTransformTarget(lo, hi)
        target.point_count = int(arr.shape[0])
        self.targets[input_id] = target

        if not MAIN_OBJECT_DISPLAY:
            self.hidden.add(input_id)
        if MAIN_OBJECT_LOCK:
            self.locked.add(input_id)
        self._apply_saved_attrs(input_id)
        logger.info(
            'Transform target initialized: id=%s pivot=%s size=%s',
            input_id, target.pivot.tolist(), target.initial_size.tolist(),
        )
        return target

    def _apply_saved_attrs(self, input_id: str) -> None:
        saved = self._saved_attrs.get(input_id)
        if not saved:
            return
        if saved.get('hidden'):
            self.hidden.add(input_id)
        else:
            self.hidden.discard(input_id)
        if saved.get('locked'):
            self.locked.add(input_id)
        else:
            self.locked.discard(input_id)

    def select(self, input_id: str | None) -> None:

        if self.solo_owner_name is not None:
            allowed = input_id is None or (
                self.solo_id is not None and input_id == self.solo_id)
            if not allowed:
                if input_id is not None:
                    set_message_overlay(
                        self._window,
                        f'{keep_case(self.solo_owner_name)} is Soloed. '
                        'Disable Solo to select other objects.',
                    )
                return
        if self.selected_id == input_id:
            return
        self.selected_id = input_id

        self.tool_mode = TOOL_NONE
        if input_id is None:
            overlay_event(logger, 'Object', 'Deselect', to_file=True)

            reset_attr_overlay_if_idle(self._window)
            return
        self._reveal_and_deselect_region()
        name = display_name(self._window, input_id)
        tgt = f'Object({name})'
        overlay_event(logger, tgt, 'Select', to_file=True)

        if self.is_locked(input_id):
            set_message_overlay(
                self._window, f'{keep_case(name)} LOCKED')

        fn = getattr(self._window, 'set_active_seq_input', None)
        if fn is not None:
            fn(input_id)

    def _reveal_and_deselect_region(self) -> None:
        win = self._window
        if win is None:
            return
        widget = getattr(win, '_widget', None)
        if widget is not None:
            widget._attr_overlay_hidden = False
        reg = getattr(win, '_region_volume_registry', None)
        if reg is not None:
            reg.user_selected = False

    def get_selected_target(self) -> InputTransformTarget | None:
        if self.selected_id is None:
            return None
        return self.targets.get(self.selected_id)

    def is_visible(self) -> bool:
        return self.selected_id is not None

    @property
    def target(self) -> InputTransformTarget | None:
        return self.get_selected_target()

    def on_change(self) -> None:
        render = getattr(self._window, '_render_current', None)
        if render is not None:
            render()
            return
        widget = getattr(self._window, '_widget', None)
        if widget is not None:
            widget.update()

    def on_commit(self) -> None:
        self.on_change()
