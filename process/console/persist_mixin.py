import logging
import sys
from pathlib import Path
from types import ModuleType

from process.console.defaults import (
    ensure_default_json, pristine_constants, user_default_path)
from process.console.persist import (
    apply_constants,
    collect_constants,
    find_settings_module,
    load_override_file,
    save_override_file,
    write_constants_to_settings,
)
from process.console.uservars import (
    own_user_vars, register_user_vars, split_user_vars)
from process.handle import set_message_overlay

logger = logging.getLogger(__name__)

class ConsolePersistMixin:

    def _persist_constants(self, module) -> dict:

        constants = collect_constants(module)
        user = own_user_vars(getattr(self, '_window', None),
                             str(self.settings_module_path()))
        if not user:
            return constants
        merged = dict(user)
        merged.update(constants)
        return merged

    def _restore_constants(self, settings_path, data: dict) -> dict:

        constants = data.get('constants') or {}
        settings_c, user = split_user_vars(
            constants, find_settings_module(str(settings_path)))
        register_user_vars(
            getattr(self, '_window', None), str(settings_path), user)
        return settings_c

    _persist_label: str = 'PLUGIN'

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
        self.system.dump_defaults(module)
        return module

    def on_settings_reload(self, module) -> None:
        self.system.apply_defaults(module)

    def ensure_default_json(self) -> Path | None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return None
        return ensure_default_json(str(settings_path))

    def export_override(self, path: str) -> None:
        module = self.sync_module_from_state()
        if module is None:
            return
        save_override_file(
            Path(path),
            {'constants': self._persist_constants(module)})
        self._notify(f'{self._persist_label} preset saved')

    def load_override_from(self, path: str) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        data = load_override_file(Path(path))
        module = apply_constants(
            str(settings_path),
            self._restore_constants(settings_path, data))
        if module is not None:
            self.on_settings_reload(module)
        self._notify(f'{self._persist_label} settings applied')

    def reset_to_plugin_default(self) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        module = apply_constants(
            str(settings_path), pristine_constants(str(settings_path)))
        if module is not None:
            self.on_settings_reload(module)
        self._notify(f'{self._persist_label} reset to default')

    def reset_to_user_default(self) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        path = user_default_path(str(settings_path))
        if not load_override_file(path):
            self._notify(f'{self._persist_label} no user default saved')
            return
        self.load_override_from(str(path))

    def set_as_user_default(self) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        module = self.sync_module_from_state()
        if module is None:
            return
        save_override_file(
            user_default_path(str(settings_path)),
            {'constants': self._persist_constants(module)})
        self._notify(f'{self._persist_label} user default saved')

    def promote_user_default(self) -> None:
        settings_path = self.settings_module_path()
        if settings_path is None:
            return
        constants = load_override_file(
            user_default_path(str(settings_path))).get('constants') or {}
        if not constants:
            self._notify(f'{self._persist_label} no user default saved')
            return
        count = write_constants_to_settings(str(settings_path), constants)
        self.ensure_default_json()
        self._notify(
            f'{self._persist_label} defaults promoted ({count})')

    def _notify(self, text: str) -> None:
        window = getattr(self, '_window', None)
        if window is not None:
            set_message_overlay(window, text)
        logger.info(text)
