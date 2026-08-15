import logging
import sys
from pathlib import Path
from types import ModuleType

from process.console.persist import find_settings_module
from process.handle import overlay_event
from process.component.region_volume.settings import (
    VOLUME_SHAPE_POLYGON, VOLUME_SHAPE_RATIOS,
)

logger = logging.getLogger(__name__)

class RegionSettingsMixin:

    def settings_module_path(self) -> Path | None:
        module = sys.modules.get(type(self).__module__)
        file = getattr(module, '__file__', None)
        if file is None:
            return None
        path = Path(file).parent / 'settings.py'
        return path if path.is_file() else None

    def sync_module_from_state(self) -> ModuleType | None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return None
        module = find_settings_module(str(settings_path))
        if module is None:
            return None
        system = getattr(self, 'system', None)
        dumper = getattr(system, 'dump_defaults', None)
        if callable(dumper):
            dumper(module)
        vis = getattr(self, 'region_visible', None)
        if vis is not None and hasattr(module, 'DEFAULT_VISIBILITY'):
            module.DEFAULT_VISIBILITY = bool(vis)
        active = self._current_active(system)
        if active is not None and hasattr(module, 'DEFAULT_ACTIVE'):
            module.DEFAULT_ACTIVE = bool(active)
        shape = getattr(self, 'shape', None)
        if shape is not None and hasattr(module, 'VOLUME_SHAPE'):
            module.VOLUME_SHAPE = shape
        return module

    def on_settings_reload(self, module: ModuleType) -> None:
        shape = getattr(module, 'VOLUME_SHAPE', None)
        if shape and shape != self.shape:
            self.rebuild_region(shape)
        self._reapply_move_duration(module)
        system = getattr(self, 'system', None)
        applier = getattr(system, 'apply_defaults', None)
        if callable(applier):
            applier(module)
            self._apply_default_toggles(module, system)
            return
        reset = getattr(system, 'reset', None)
        if not callable(reset):
            self._apply_default_toggles(module, system)
            return
        active = getattr(system, 'active', None)
        reset()
        if active is not None:
            system.active = active
        self._apply_default_toggles(module, system)

    def _reapply_move_duration(self, module) -> None:
        win = self._window
        if win is None:
            return
        value = getattr(module, 'KEYFRAME_MOVE_DURATION', None)
        if value is None:
            return
        annot = getattr(win, '_annot_animator', None)
        if annot is not None:
            annot.set_duration_ms(value)
        for listener in getattr(win, '_duration_listeners', []):
            listener(value)

    def _apply_default_toggles(self, module, system) -> None:
        vis = getattr(module, 'DEFAULT_VISIBILITY', None)
        if vis is not None:
            self.region_visible = bool(vis)
        act = getattr(module, 'DEFAULT_ACTIVE', None)
        if act is not None:
            self._set_active(system, bool(act))

    def _current_active(self, system):
        if system is not None and hasattr(system, 'active'):
            return system.active
        if hasattr(self, 'active'):
            return self.active
        return None

    def _set_active(self, system, value: bool) -> None:
        if system is not None and hasattr(system, 'active'):
            system.active = value
        elif hasattr(self, 'active'):
            self.active = value

    def rebuild_region(self, shape: str) -> None:
        from process.component.region_volume.factory import make_region
        if shape == self.shape:
            return
        old = self.region
        scale = max(float(x) for x in old.size)
        ratio = VOLUME_SHAPE_RATIOS.get(shape, (1.0, 1.0, 1.0))
        size = tuple(float(r) * scale for r in ratio)
        new = make_region(
            shape,
            center=tuple(float(x) for x in old.center),
            size=size,
            softness=float(old.softness),
        )
        new.rotation = old.rotation.copy()
        if shape == VOLUME_SHAPE_POLYGON:
            new.center = old.center.copy()
        self.region = new
        self.shape = shape
        self.on_region_rebuilt(new)
        self.save_region()
        overlay_event(logger, f'Region({self.overlay_label or "region"})',
                      'Update', attr='Shape', value=shape, to_file=True)

    def on_region_rebuilt(self, region) -> None:
        system = getattr(self, 'system', None)
        if system is not None:
            system.region = region
