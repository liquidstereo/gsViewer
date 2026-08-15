import logging
import sys
from pathlib import Path
from types import ModuleType

logger = logging.getLogger(__name__)

def _find_module_for_path(path: str) -> ModuleType | None:
    resolved = str(Path(path).resolve())
    for module in list(sys.modules.values()):
        file = getattr(module, '__file__', None)
        if file and str(Path(file).resolve()) == resolved:
            return module
    return None

def _propagate(module: ModuleType, changed: dict) -> None:
    name = getattr(module, '__name__', '')
    if '.' not in name:
        return
    package = name.rsplit('.', 1)[0]
    prefix = package + '.'
    for mod in list(sys.modules.values()):
        mod_name = getattr(mod, '__name__', '')
        if mod is module:
            continue
        if mod_name != package and not mod_name.startswith(prefix):
            continue
        for key, value in changed.items():
            if hasattr(mod, key):
                setattr(mod, key, value)

def reapply_attrs(
    target: object, module: ModuleType, mapping: dict,
    int_attrs: tuple = (),
) -> None:
    for attr, const in mapping.items():
        if not hasattr(module, const):
            continue
        value = getattr(module, const)
        setattr(target, attr, int(value) if attr in int_attrs else value)

def dump_attrs(source: object, module: ModuleType, mapping: dict) -> None:
    for attr, const in mapping.items():
        if hasattr(source, attr) and hasattr(module, const):
            setattr(module, const, getattr(source, attr))

def apply_source(path: str, source: str) -> ModuleType | None:
    try:
        code = compile(source, path, 'exec')
    except SyntaxError:
        return None
    module = _find_module_for_path(path)
    namespace = dict(module.__dict__) if module is not None else {}
    try:

        exec(code, namespace)
    except Exception as e:
        logger.warning('Hot reload exec failed: %s', e)
        return None
    if module is None:
        return None
    changed = {}
    for key, value in namespace.items():
        if key.startswith('__'):
            continue
        setattr(module, key, value)
        changed[key] = value
    _propagate(module, changed)
    logger.info('Hot reload applied: %s', Path(path).name)
    return module
