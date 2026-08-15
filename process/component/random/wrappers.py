import logging
import re

import numpy as np

from process.component.random.engine import deterministic_unit, random_eval

logger = logging.getLogger(__name__)

_AXES = ('x', 'y', 'z')
APPLY_MODES = ('offset', 'absolute')

_RV_BASE = 0.5
_RV_MIN = 0.0
_RV_MAX = 1.0
_RV_KEY = '__random_value__'

def _resolve_object(window):

    controller = getattr(window, '_input_transform', None)
    if controller is None:
        return None, None
    sel = controller.selected_id
    if sel is None:
        ids = list(controller.targets.keys())
        sel = ids[0] if len(ids) == 1 else None
    if sel is None:
        return controller, None
    return controller, sel

def _axis_values(component, base: np.ndarray, dist: float,
                 key_prefix: tuple, mode: str) -> np.ndarray:
    out = np.asarray(base, dtype=np.float32).copy()
    for i, axis in enumerate(_AXES):
        r = random_eval(component, float(dist), (*key_prefix, axis))
        out[i] = float(base[i]) + r if mode == 'offset' else r
    return out

def randomize_object_center(window, dist: float,
                            mode: str = 'offset') -> bool:

    from process.common.widget import request_repaint
    from process.undo import record_transform, snapshot_transform
    component = getattr(window, '_random_component', None)
    controller, sel = _resolve_object(window)
    if component is None or controller is None:
        return False
    if sel is None:
        logger.warning('Randomize object center: no target selected')
        return False
    target = controller.targets.get(sel)
    if target is None:
        return False
    m = mode if mode in APPLY_MODES else 'offset'
    before = snapshot_transform(target)
    target.center = _axis_values(
        component, target.center, dist, ('object', sel, 'center'), m)
    after = snapshot_transform(target)
    record_transform(window, controller, sel, before, after)
    on_change = getattr(controller, 'on_change', None)
    if callable(on_change):
        on_change()
    request_repaint(window)
    logger.info(
        'Randomize object center: %s mode=%s dist=%s', sel, m, dist)
    return True

def _var_name(section: str, label: str) -> str:
    raw = f'{section}_{label}'.lower()
    return 'attr_' + re.sub(r'\W+', '_', raw).strip('_')

class AttrRandomApplier:
    def __init__(self, system) -> None:
        self.system = system
        self.targets: dict = {}
        self._random_value: float = _RV_BASE

    def is_active(self, section: str, label: str) -> bool:
        return (section, label) in self.targets

    def toggle_target(self, section: str, label: str, spec) -> None:
        key = (section, label)
        existing = self.targets.pop(key, None)
        if existing is not None:
            if existing['setter'] is not None:
                existing['setter'](existing['base'])
            logger.info('Apply Random OFF: %s/%s', section, label)
            return
        options = tuple(getattr(spec, 'options', ()) or ())
        if options:
            base = spec.get() if spec.get is not None else options[0]
            self.targets[key] = {
                'setter': spec.set, 'options': options,
                'base': base, 'value': base,
            }
        else:
            base = float(spec.get()) if spec.get is not None else 0.0
            self.targets[key] = {
                'setter': spec.set,
                'vmin': float(spec.vmin),
                'vmax': float(spec.vmax),
                'base': base,
                'value': base,
            }
        logger.info('Apply Random ON: %s/%s', section, label)

    def clear(self) -> None:
        if not self.targets:
            return
        for target in self.targets.values():
            if target['setter'] is not None:
                target['setter'](target['base'])
        self.targets.clear()
        logger.info('Apply Random cleared all targets')

    def set_base(
        self, section: str, label: str, value: float | str,
    ) -> None:
        target = self.targets.get((section, label))
        if target is not None:
            target['base'] = (
                value if target.get('options') else float(value))

    def apply_frame(
        self, frame_idx: int, skip: tuple | None = None
    ) -> None:
        grouper = getattr(self.system, 'frame_group', None)
        group = grouper(frame_idx) if callable(grouper) else frame_idx
        output = getattr(self.system, 'random_output', None)
        if callable(output):
            self._random_value = output(group)
        else:
            self._random_value = self.system.shape(
                _RV_BASE, _RV_MIN, _RV_MAX, _RV_KEY, group)
        if not self.targets:
            return
        for (section, label), target in self.targets.items():
            if skip is not None and (section, label) == skip:
                continue
            options = target.get('options')
            if options:
                value = self._pick_option(options, section, label, group)
            else:
                value = self.system.shape(
                    target['base'], target['vmin'], target['vmax'],
                    section, label, group)
            target['value'] = value
            if target['setter'] is not None:
                target['setter'](value)

    def _pick_option(
        self, options: tuple, section: str, label: str, group: object,
    ) -> str:
        seed = float(getattr(self.system, 'seed', 0.0))
        r = deterministic_unit(seed, section, label, group)
        idx = min(len(options) - 1, int(r * len(options)))
        return options[idx]

    def current_output(self) -> float:
        return float(self._random_value)

    def value_namespace(self) -> dict:
        ns: dict = {}
        for (section, label), target in self.targets.items():
            val = target['value']
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                ns[_var_name(section, label)] = float(val)
        return ns

def reset_window_attr_random(window) -> None:
    applier = getattr(window, '_attr_random', None)
    if applier is None:
        return
    clear = getattr(applier, 'clear', None)
    if callable(clear):
        clear()
    system = getattr(applier, 'system', None)
    reset = getattr(system, 'reset', None)
    if callable(reset):
        reset()
