import importlib.util
import json
import logging
from pathlib import Path

from process.console.persist import (
    collect_constants, find_settings_module, load_override_file,
    save_override_file,
)

logger = logging.getLogger(__name__)

_DEFAULT_JSON_NAME = 'default.json'
_USER_DEFAULT_JSON_NAME = 'user_default.json'

def default_json_path(settings_path: str) -> Path:
    return Path(settings_path).resolve().parent / _DEFAULT_JSON_NAME

def user_default_path(settings_path: str) -> Path:
    return Path(settings_path).resolve().parent / _USER_DEFAULT_JSON_NAME

def _exec_pristine(settings_path: str) -> dict | None:
    path = Path(settings_path).resolve()
    name = f'_pristine_{path.parent.name}_{path.stem}'
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ImportError, SyntaxError, NameError, AttributeError, TypeError,
            ValueError, OSError) as e:
        logger.warning('Pristine settings load failed: %s', e)
        return None
    return collect_constants(module)

def pristine_constants(settings_path: str) -> dict:
    constants = _exec_pristine(settings_path)
    if constants is not None:
        return constants
    module = find_settings_module(settings_path)
    return collect_constants(module) if module is not None else {}

def matches_default(path: Path, data: dict) -> bool:
    existing = load_override_file(path)
    if not existing:
        return False
    return existing == json.loads(json.dumps(data))

def ensure_default_json(settings_path: str) -> Path:
    path = default_json_path(settings_path)
    constants = pristine_constants(settings_path)
    if not constants:
        return path
    data = {'constants': constants}
    if matches_default(path, data):
        return path
    save_override_file(path, data)
    logger.info('default.json synced (constants): %s', path.name)
    return path

def apply_startup_defaults(plugin) -> bool:
    getter = getattr(plugin, 'settings_module_path', None)
    load = getattr(plugin, 'load_override_from', None)
    if not (callable(getter) and callable(load)):
        return False
    settings_path = getter()
    if settings_path is None:
        return False
    module = find_settings_module(str(settings_path))
    mode = getattr(module, 'STARTUP_DEFAULTS', 'plugin_default')
    if mode != 'user_default':
        return False
    path = user_default_path(str(settings_path))
    if not load_override_file(path):
        logger.info('Startup user default missing: %s', path)
        return False
    load(str(path))
    logger.info(
        'Startup defaults: user default applied (%s)',
        Path(settings_path).parent.name)
    return True

def load_default(json_path: Path) -> dict:
    return load_override_file(Path(json_path))
