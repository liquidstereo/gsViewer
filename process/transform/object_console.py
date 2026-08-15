import logging
from pathlib import Path

from process.common import display_name
from process.common.widget import request_repaint
from process.overlay_coord_io import (
    display_center_axis, display_euler_axis, display_scale_axis,
    set_display_center_axis, set_display_euler_axis, set_display_scale_axis)
from process.console import open_script_console
from process.console.contributors import (
    apply_contributor_sections, merge_contributor_snapshots)
from process.console.defaults import ensure_default_json
from process.console.live_expr import apply_expr_constants
from process.console.persist import (
    collect_constants, load_override_file, save_override_file)
from process.transform import object_console_settings as _settings

logger = logging.getLogger(__name__)

_SETTINGS_PATH = str(Path(_settings.__file__).resolve())

_DEFAULT_MAP = {
    'point_size': 'POINT_SIZE',
    'position_x': 'POSITION_X',
    'position_y': 'POSITION_Y',
    'position_z': 'POSITION_Z',
    'rotate_x': 'ROTATE_X',
    'rotate_y': 'ROTATE_Y',
    'rotate_z': 'ROTATE_Z',
    'scale_x': 'SCALE_X',
    'scale_y': 'SCALE_Y',
    'scale_z': 'SCALE_Z',
}
_DEFAULT_INTS = ()

class ObjectConsoleSystem:

    def __init__(self, window) -> None:
        self._window = window

    def _resolve(self):

        c = getattr(self._window, '_input_transform', None)
        if c is None:
            return None, None, None
        sel = c.selected_id
        if sel is None:
            ids = list(c.targets.keys())
            sel = ids[0] if len(ids) == 1 else None
        if sel is None:
            return c, None, None
        return c, c.targets.get(sel), sel

    @property
    def point_size(self) -> float:
        c, _t, sel = self._resolve()
        return c.get_point_scale(sel) if sel is not None else 1.0

    @point_size.setter
    def point_size(self, value: float) -> None:
        c, _t, sel = self._resolve()
        if sel is not None:
            c.set_point_scale(sel, max(0.0, float(value)))

    def _pos(self, i: int) -> float:
        _c, t, _sel = self._resolve()
        if t is None:
            return 0.0
        return display_center_axis(t.center, i)

    def _set_pos(self, i: int, value: float) -> None:
        _c, t, _sel = self._resolve()
        if t is None:
            return
        t.center = set_display_center_axis(t.center, i, value)

    def _rot(self, i: int) -> float:
        _c, t, _sel = self._resolve()
        if t is None:
            return 0.0
        return display_euler_axis(t.rotation, i)

    def _set_rot(self, i: int, value: float) -> None:
        _c, t, _sel = self._resolve()
        if t is None:
            return
        t.rotation = set_display_euler_axis(t.rotation, i, value)

    def _scale(self, i: int) -> float:
        _c, t, _sel = self._resolve()
        if t is None:
            return 1.0
        return display_scale_axis(t.size, t.initial_size, i)

    def _set_scale(self, i: int, value: float) -> None:
        _c, t, _sel = self._resolve()
        if t is None:
            return
        t.size = set_display_scale_axis(
            t.size, t.initial_size, i, value)

    position_x = property(lambda s: s._pos(0),
                          lambda s, v: s._set_pos(0, v))
    position_y = property(lambda s: s._pos(1),
                          lambda s, v: s._set_pos(1, v))
    position_z = property(lambda s: s._pos(2),
                          lambda s, v: s._set_pos(2, v))
    rotate_x = property(lambda s: s._rot(0),
                        lambda s, v: s._set_rot(0, v))
    rotate_y = property(lambda s: s._rot(1),
                        lambda s, v: s._set_rot(1, v))
    rotate_z = property(lambda s: s._rot(2),
                        lambda s, v: s._set_rot(2, v))
    scale_x = property(lambda s: s._scale(0),
                       lambda s, v: s._set_scale(0, v))
    scale_y = property(lambda s: s._scale(1),
                       lambda s, v: s._set_scale(1, v))
    scale_z = property(lambda s: s._scale(2),
                       lambda s, v: s._set_scale(2, v))

class ObjectConsolePlugin:

    overlay_label: str = 'OBJECT'

    def __init__(self, window) -> None:
        self._window = window
        self.system = ObjectConsoleSystem(window)

    def console_title(self) -> str | None:
        _, _, sel = self.system._resolve()
        if sel is None:
            return None
        return display_name(self._window, sel)

    def settings_module_path(self) -> str:
        return _SETTINGS_PATH

    def ensure_default_json(self) -> None:
        ensure_default_json(_SETTINGS_PATH)

    def sync_module_from_state(self):
        _c, t, _sel = self.system._resolve()
        if t is None:
            return None
        s = self.system
        _settings.POINT_SIZE = s.point_size
        _settings.POSITION_X = s.position_x
        _settings.POSITION_Y = s.position_y
        _settings.POSITION_Z = s.position_z
        _settings.ROTATE_X = s.rotate_x
        _settings.ROTATE_Y = s.rotate_y
        _settings.ROTATE_Z = s.rotate_z
        _settings.SCALE_X = s.scale_x
        _settings.SCALE_Y = s.scale_y
        _settings.SCALE_Z = s.scale_z
        return _settings

    def on_settings_reload(self, module) -> None:
        _c, t, _sel = self.system._resolve()
        if t is None:
            return
        s = self.system
        s.point_size = getattr(module, 'POINT_SIZE', s.point_size)
        s.position_x = getattr(module, 'POSITION_X', s.position_x)
        s.position_y = getattr(module, 'POSITION_Y', s.position_y)
        s.position_z = getattr(module, 'POSITION_Z', s.position_z)
        s.rotate_x = getattr(module, 'ROTATE_X', s.rotate_x)
        s.rotate_y = getattr(module, 'ROTATE_Y', s.rotate_y)
        s.rotate_z = getattr(module, 'ROTATE_Z', s.rotate_z)
        s.scale_x = getattr(module, 'SCALE_X', s.scale_x)
        s.scale_y = getattr(module, 'SCALE_Y', s.scale_y)
        s.scale_z = getattr(module, 'SCALE_Z', s.scale_z)
        request_repaint(self._window)

    def export_override(self, path) -> None:
        module = self.sync_module_from_state()
        constants = collect_constants(module) if module is not None else {}
        data: dict = {'constants': constants}
        if self._window is not None:
            merge_contributor_snapshots(self._window, data)
        save_override_file(Path(path), data)
        logger.info('Object preset exported: %s', Path(path).name)

    def load_override_from(self, path) -> None:
        data = load_override_file(Path(path))
        if not data:
            return
        constants = data.get('constants') or {}
        if constants and self._window is not None:
            module = apply_expr_constants(
                self._window, self, self.settings_module_path(), constants)
            if module is not None:
                self.on_settings_reload(module)
        if self._window is not None:
            apply_contributor_sections(self._window, data)
        request_repaint(self._window)
        logger.info('Object preset loaded: %s', Path(path).name)

def open_object_console(window) -> None:
    plugin = ObjectConsolePlugin(window)
    _c, t, _sel = plugin.system._resolve()
    if t is None:
        logger.warning('Object console: no target selected')
        return
    open_script_console(window, plugin)

def apply_object_preset(window) -> None:
    from PySide6.QtWidgets import QFileDialog
    plugin = ObjectConsolePlugin(window)
    _c, t, _sel = plugin.system._resolve()
    if t is None:
        logger.warning('Apply object preset: no target selected')
        return
    path, _ = QFileDialog.getOpenFileName(
        window, 'Apply Object Preset', '', 'JSON (*.json)')
    if path:
        plugin.load_override_from(path)
