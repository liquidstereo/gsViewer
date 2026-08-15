import logging
from typing import Callable

from process.component.region_volume.palette_auto import auto_hue_color
from process.component.region_volume.settings import (
    REGION_VOLUME_KEY_KEYFRAME_ADD, REGION_VOLUME_KEY_KEYFRAME_CLEAR,
    REGION_VOLUME_KEY_KEYFRAME_NEXT, REGION_VOLUME_KEY_KEYFRAME_PREV,
    REGION_VOLUME_KEY_KEYFRAME_REMOVE, REGION_VOLUME_KEY_KEYFRAME_TOGGLE,
    REGION_VOLUME_KEY_VISIBLE, TOOL_NONE,
)

logger = logging.getLogger(__name__)

_KEYS_ALLOWED_WHEN_HIDDEN: frozenset[str] = frozenset({
    REGION_VOLUME_KEY_VISIBLE,
    REGION_VOLUME_KEY_KEYFRAME_TOGGLE,
    REGION_VOLUME_KEY_KEYFRAME_ADD,
    REGION_VOLUME_KEY_KEYFRAME_REMOVE,
    REGION_VOLUME_KEY_KEYFRAME_CLEAR,
    REGION_VOLUME_KEY_KEYFRAME_PREV,
    REGION_VOLUME_KEY_KEYFRAME_NEXT,
})

class RegionVolumeRegistry:

    def __init__(self) -> None:
        self.members: list = []
        self.palettes: list = []
        self.selected_index: int = -1

        self.user_selected: bool = False

        self.solo_index: int = -1

        self._solo_saved_vis: dict = {}
        self.key_handlers: dict = {}
        self.release_handlers: dict = {}

        self.hidden_allowed_keys: set[str] = set()
        self._num_bound: bool = False

    def register(self, ctrl, palette=None) -> int:
        self.members.append(ctrl)
        self.palettes.append(palette)
        idx = len(self.members) - 1
        if idx == 0:
            self.selected_index = 0
        else:
            ctrl.tool_mode = TOOL_NONE
            self._recolor()
        logger.info(
            'RegionVolume registered: %s (idx=%d)',
            getattr(ctrl, 'overlay_label', '') or 'region', idx,
        )
        return idx

    def _recolor(self) -> None:
        total = len(self.members)
        for i, pal in enumerate(self.palettes):
            if pal is None:
                continue
            pal.color = auto_hue_color(i, total)

    def count(self) -> int:
        return len(self.members)

    def index_of(self, ctrl) -> int:
        for i, m in enumerate(self.members):
            if m is ctrl:
                return i
        return -1

    def selected(self):
        if 0 <= self.selected_index < len(self.members):
            return self.members[self.selected_index]
        return None

    def is_selected(self, ctrl) -> bool:
        return self.selected() is ctrl

    def solo_active(self) -> bool:
        return 0 <= self.solo_index < len(self.members)

    def solo_member(self):
        return self.members[self.solo_index] if self.solo_active() else None

    def is_soloed(self, ctrl) -> bool:
        return self.solo_active() and self.members[self.solo_index] is ctrl

    def is_active_selection(self, ctrl) -> bool:
        return self.user_selected and self.is_selected(ctrl)

    def color_for(self, ctrl) -> str | None:
        if len(self.members) <= 1:
            return None
        i = self.index_of(ctrl)
        if i < 0:
            return None
        return auto_hue_color(i, len(self.members))

    def set_selected(self, ctrl) -> None:
        i = self.index_of(ctrl)
        if i < 0:
            return
        self.selected_index = i
        self.user_selected = True
        for j, m in enumerate(self.members):
            if j != i:
                m.tool_mode = TOOL_NONE

    def unregister(self, ctrl) -> bool:
        i = self.index_of(ctrl)
        if i < 0:
            return False
        self.members.pop(i)
        self.palettes.pop(i)
        self.selected_index = 0 if self.members else -1
        self.user_selected = False
        if self.solo_index == i:
            self.solo_index = -1
        elif self.solo_index > i:
            self.solo_index -= 1
        self._solo_saved_vis.pop(ctrl, None)
        self._recolor()
        return True

    def reinsert(self, ctrl, palette, index: int) -> None:
        if ctrl in self.members:
            return
        index = max(0, min(index, len(self.members)))
        self.members.insert(index, ctrl)
        self.palettes.insert(index, palette)
        self._recolor()

    def bind_handler(
        self, key: str, ctrl, handler: Callable,
        allow_when_hidden: bool = False,
    ) -> bool:
        first = key not in self.key_handlers
        self.key_handlers.setdefault(key, {})[ctrl] = handler
        if allow_when_hidden:
            self.hidden_allowed_keys.add(key)
        return first

    def bind_release_handler(
        self, key: str, ctrl, handler: Callable,
        allow_when_hidden: bool = False,
    ) -> bool:
        first = key not in self.release_handlers
        self.release_handlers.setdefault(key, {})[ctrl] = handler
        if allow_when_hidden:
            self.hidden_allowed_keys.add(key)
        return first

    def _key_allowed(self, ctrl, key: str) -> bool:
        if key in _KEYS_ALLOWED_WHEN_HIDDEN or key in self.hidden_allowed_keys:
            return True
        vis = getattr(ctrl, 'is_visible', None)
        return vis() if callable(vis) else True

    def handler_for(self, key: str) -> Callable | None:
        ctrl = self.selected()
        if ctrl is None or not self._key_allowed(ctrl, key):
            return None
        return self.key_handlers.get(key, {}).get(ctrl)

    def release_handler_for(self, key: str) -> Callable | None:
        ctrl = self.selected()
        if ctrl is None or not self._key_allowed(ctrl, key):
            return None
        return self.release_handlers.get(key, {}).get(ctrl)

def renumber_box_labels(window, base_label: str) -> None:
    if not base_label:
        return
    reg = get_registry(window)
    siblings = [m for m in reg.members
                if getattr(m, '_base_label', None) == base_label]
    multi = len(siblings) > 1
    for i, member in enumerate(siblings):
        label = f'{base_label} {i + 1}' if multi else base_label
        if getattr(member, 'overlay_label', None) != label:
            member.overlay_label = label
            member.relabel_paths(window)

def get_registry(window) -> RegionVolumeRegistry:
    reg = getattr(window, '_region_volume_registry', None)
    if reg is None:
        reg = RegionVolumeRegistry()
        window._region_volume_registry = reg
    return reg
