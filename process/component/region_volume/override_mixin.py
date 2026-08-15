import logging
from pathlib import Path

from process.console.contributors import (
    apply_contributor_sections, merge_contributor_snapshots,
)
from process.console.defaults import (
    default_json_path, matches_default, pristine_constants,
    user_default_path,
)
from process.console.live_expr import apply_expr_constants, inject_expr_text
from process.console.persist import (
    apply_constants, collect_constants, find_settings_module,
    load_override_file, save_override_file, write_constants_to_settings,
)
from process.console.reload import _propagate
from process.handle import overlay_event
from process.widget.text_case import keep_case
from process.component.region_volume.attr_persist import (
    curve_defaults, defaults, restore, snapshot,
)
from process.component.region_volume.keys import show_message_overlay
from process.component.region_volume.region_console import (
    RegionTransformSystem, vec_attr_map,
)

logger = logging.getLogger(__name__)

class OverrideMixin:

    def load_override_from(self, path: str | Path) -> None:
        data = load_override_file(Path(path))
        if not data:
            return
        self.apply_override_data(
            data, f'OVERRIDE LOADED: {keep_case(Path(path).name)}',
        )

    def apply_override_data(
        self, data: dict, notice: str | None = None,
    ) -> None:
        if not data:
            return
        attrs = data.get('attrs') or {}
        build = self._attr_build_specs
        if attrs and callable(build):
            restore(build(), attrs)
        constants = data.get('constants') or {}
        settings_path = self.settings_module_path()
        if constants and settings_path is not None:
            if self._window is not None:
                module = apply_expr_constants(
                    self._window, self, str(settings_path), constants)
            else:
                module = apply_constants(str(settings_path), constants)
            if module is not None:
                self.on_settings_reload(module)
        self._restore_transform(data.get('transform'))
        curves = data.get('curves')
        if curves:
            self.apply_curve_state(curves)
        if self._window is not None:
            apply_contributor_sections(self._window, data)
        if notice:
            self._notify_override(notice)

    def _restore_transform(self, transform) -> None:
        if not transform:
            return
        self.region.from_dict(transform)
        self.save_region()
        self.on_change()

    def restore_pending_attrs(self, build_specs) -> None:
        self._attr_build_specs = build_specs
        if self._pending_attrs:
            restore(build_specs(), self._pending_attrs)
            self._pending_attrs = {}

    def _console_prefix(self) -> str:

        return (self.overlay_label or 'REGION').upper().replace(' ', '')

    def expr_vector_system(self) -> RegionTransformSystem:
        return RegionTransformSystem(lambda: self.region)

    def expr_vector_attr_map(self) -> dict:
        return vec_attr_map(self._console_prefix())

    def augment_console_constants(self, constants: dict) -> None:
        if getattr(self, 'region', None) is None:
            return
        system = self.expr_vector_system()
        prefix = self._console_prefix()
        constants[f'{prefix}_POSITION'] = system.region_position
        constants[f'{prefix}_SCALE'] = system.region_scale
        constants[f'{prefix}_ROTATE'] = system.region_rotate

    def _build_override_data(self) -> dict:
        module = self.sync_module_from_state()
        constants = collect_constants(module) if module is not None else {}
        self.augment_console_constants(constants)
        settings_path = self.settings_module_path()
        if self._window is not None and settings_path is not None:
            inject_expr_text(self._window, str(settings_path), constants)
        build = self._attr_build_specs
        attrs = snapshot(build()) if callable(build) else {}
        data = {
            'constants': constants,
            'attrs': attrs,
            'transform': self.region.to_dict(),
            'curves': self.curve_state(),
        }
        if self._window is not None:
            merge_contributor_snapshots(self._window, data)
        return data

    def _build_default_data(self) -> dict:
        settings_path = self.settings_module_path()
        constants = (pristine_constants(str(settings_path))
                     if settings_path is not None else {})
        self._restore_pristine_specs(settings_path, constants)
        build = self._attr_build_specs
        attrs = defaults(build()) if callable(build) else {}
        curves = curve_defaults(build()) if callable(build) else {}
        transform = self._default_transform or self.region.to_dict()
        return {
            'constants': constants,
            'attrs': attrs,
            'transform': transform,
            'curves': curves,
        }

    def _restore_pristine_specs(
        self, settings_path, constants: dict,
    ) -> None:
        if settings_path is None or not constants:
            return
        module = find_settings_module(str(settings_path))
        if module is not None:
            _propagate(module, constants)

    def ensure_default_json(self) -> Path | None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return None
        path = default_json_path(str(settings_path))
        data = self._build_default_data()
        if not matches_default(path, data):
            save_override_file(path, data)
            logger.info('default.json synced (full): %s', path.name)
        return path

    def _notify_override(self, text: str, log: bool = True) -> None:
        win = self._window
        if win is None:
            return
        show_message_overlay(win, text)
        if log:
            overlay_event(
                logger, f'Region({self.overlay_label or "region"})',
                'Save', attr='Settings', to_file=True,
            )

    def export_override(self, path: str | Path) -> None:
        save_override_file(Path(path), self._build_override_data())
        self._notify_override(
            f'SETTINGS EXPORTED: {keep_case(Path(path).name)}',
        )

    def reset_to_plugin_default(self) -> None:
        json_path = self.ensure_default_json()
        if json_path is not None:
            self.load_override_from(str(json_path))

    def reset_to_user_default(self) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        path = user_default_path(str(settings_path))
        if not load_override_file(path):
            self._notify_override('NO USER DEFAULT SAVED')
            return
        self.load_override_from(str(path))

    def set_as_user_default(self) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        save_override_file(
            user_default_path(str(settings_path)),
            self._build_override_data())
        self._notify_override('USER DEFAULT SAVED')

    def promote_user_default(self) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        constants = load_override_file(
            user_default_path(str(settings_path))).get('constants') or {}
        if not constants:
            self._notify_override('NO USER DEFAULT SAVED')
            return
        count = write_constants_to_settings(str(settings_path), constants)
        self.ensure_default_json()
        self._notify_override(f'DEFAULTS PROMOTED: {count} constant(s)')
