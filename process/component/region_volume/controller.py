import logging
from pathlib import Path

from process.handle import overlay_event, set_message_overlay
from process.component.region_volume.controller_paths import RegionPathsMixin
from process.component.region_volume.controller_settings import RegionSettingsMixin
from process.component.region_volume.override_mixin import OverrideMixin
from process.component.region_volume.factory import make_region
from process.component.region_volume.keyframes import RegionVolumeKeyframes
from process.component.region_volume.keys import make_reset_to_default
from process.component.region_volume.region import RegionBox
from process.component.region_volume.settings import (
    REGION_CENTER, REGION_SIZE, REGION_SOFTNESS,
    REGION_VOLUME_STARTUP_VISIBILITY, REGION_VOLUME_TOOL_DEFAULT, TOOL_NONE,
    VOLUME_SHAPE,
)

logger = logging.getLogger(__name__)

class RegionVolumeBoxController(
    OverrideMixin, RegionPathsMixin, RegionSettingsMixin,
):

    region_basename: str = 'region'
    keyframes_basename: str = 'keyframes'
    curves_basename: str = 'curves'
    overlay_label: str = ''

    volume_shape: str = VOLUME_SHAPE
    startup_center: tuple[float, float, float] = REGION_CENTER
    startup_size: tuple[float, float, float] = REGION_SIZE
    startup_softness: float = REGION_SOFTNESS
    startup_visible: bool = REGION_VOLUME_STARTUP_VISIBILITY
    system_class = None

    def __init__(
        self,
        region: RegionBox | None = None,
        startup_visibility: bool | None = None,
        tool_default: str = REGION_VOLUME_TOOL_DEFAULT,
    ) -> None:
        self._window = None
        if region is None:
            region = make_region(
                self.volume_shape,
                center=self.startup_center,
                size=self.startup_size,
                softness=self.startup_softness,
            )
        self.region: RegionBox = region

        self._softness_default: float = float(self.region.softness)

        self.shape: str = 'cube'
        self.region_visible: bool = (
            self.startup_visible if startup_visibility is None
            else startup_visibility
        )
        self.region_path: Path = Path('region.json')
        self.tool_mode: str = tool_default

        self.region_locked: bool = False

        self.bracket_mode: bool = False
        self.keyframes: RegionVolumeKeyframes = RegionVolumeKeyframes()
        self.keyframes_path: Path = Path('keyframes.json')
        self.curves_path: Path = Path('curves.json')

        self._pending_attrs: dict = {}

        self._attr_build_specs = None

        self._default_transform: dict | None = None
        self.keyframe_animator = None

        self.keyframes_visible: bool = False
        if self.system_class is not None:
            self.system = self.system_class(self.region)

    def on_reset(self) -> None:
        reset = getattr(getattr(self, 'system', None), 'reset', None)
        if callable(reset):
            reset()

    def is_effect_active(self) -> bool:
        return bool(getattr(getattr(self, 'system', None), 'active', False))

    def toggle_effect_active(self) -> None:
        toggle = getattr(
            getattr(self, 'system', None), 'toggle_active', None)
        if callable(toggle):
            toggle()

    @property
    def target(self) -> RegionBox:
        return self.region

    def is_visible(self) -> bool:
        return self.region_visible

    def is_region_locked(self) -> bool:
        return self.region_locked

    def on_select(self) -> None:
        win = self._window
        if win is None:
            return
        reg = getattr(win, '_region_volume_registry', None)

        itc = getattr(win, '_input_transform', None)
        owner = getattr(itc, 'solo_owner_name', None) if itc else None
        if owner is not None and not (
                reg is not None and reg.is_soloed(self)):
            set_message_overlay(
                win,
                f'{owner} is Soloed. '
                'Disable Solo to select other objects.',
            )
            return
        if reg is not None:
            reg.set_selected(self)

        if not self.region_locked:
            self.tool_mode = REGION_VOLUME_TOOL_DEFAULT

        widget = getattr(win, '_widget', None)
        if widget is not None:
            widget._attr_overlay_hidden = False

        itc = getattr(win, '_input_transform', None)
        if itc is not None:
            itc.select(None)
        overlay_event(logger, f'Region({self.overlay_label or "region"})',
                      'Select', to_file=True)

        if self.region_locked:
            set_message_overlay(
                win, f'{self.overlay_label or "REGION"} LOCKED')

    def reset_to_default(self, window) -> None:
        make_reset_to_default(self)(window)

    def toggle_region_lock(self) -> bool:
        self.region_locked = not self.region_locked
        if self.region_locked:
            self.tool_mode = TOOL_NONE
        label = self.overlay_label or 'REGION'
        state = 'LOCKED' if self.region_locked else 'UNLOCKED'
        set_message_overlay(self._window, f'{label} {state}')
        return self.region_locked

    def on_change(self) -> None:
        animator = self.keyframe_animator
        if animator is not None:
            animator.stop()
        if self._window is not None and hasattr(self._window, '_widget'):
            self._window._widget.update()

    def on_commit(self) -> None:
        self.save_region()
        overlay_event(logger, f'Region({self.overlay_label or "region"})',
                      'Update', attr='Transform', to_file=True)
