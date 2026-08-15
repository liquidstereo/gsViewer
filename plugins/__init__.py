import importlib
import logging
import sys
from pathlib import Path

from configs.colorize import Msg
from configs.settings import IGNORE_AUDIO_INPUT

logger = logging.getLogger(__name__)

_PLUGIN_ALIASES: dict[str, str] = {'audio_analyzer': 'audio'}

_RESERVED_DIRS: set[str] = set()

_COMPONENT_PLUGINS: set[str] = {'audio', 'particle'}

def _plugin_dir() -> Path:
    return Path(__file__).parent

def list_plugins() -> list[str]:
    root = _plugin_dir()
    out: list[str] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith('_'):
            continue
        if entry.name in _RESERVED_DIRS:
            continue
        if (entry / '__init__.py').is_file():
            out.append(entry.name)
    return out

def _abort(msg: str) -> None:
    Msg.Error(msg, divide=False)
    sys.exit(1)

def _import_plugin(name: str):
    if name in _COMPONENT_PLUGINS:
        try:
            return importlib.import_module(f'process.component.{name}')
        except ImportError as e:
            _abort(f'Component import failed: "{name}" ({e})')
    plugin_root = _plugin_dir() / name
    if not plugin_root.is_dir():
        avail = ', '.join(list_plugins()) or '(none)'
        _abort(
            f'Plugin not found: "{name}". Available: {avail}'
        )
    try:
        return importlib.import_module(f'plugins.{name}')
    except ImportError as e:
        _abort(f'Plugin import failed: "{name}" ({e})')

def _check_requirements(
    name: str, requires: list[str], resources: dict
) -> None:
    for key in requires:
        if not resources.get(key):
            _abort(
                f'Plugin "{name}" requires "--{key}" argument'
            )

def load_plugin(
    name: str | None, resources: dict | None = None
) -> object | None:
    if not name:
        return None
    resources = resources or {}
    mod = _import_plugin(name)
    requires = getattr(mod, 'REQUIRES', [])
    _check_requirements(name, requires, resources)
    factory = getattr(mod, 'create_plugin', None)
    if factory is None:
        _abort(
            f'Plugin "{name}" missing create_plugin() in __init__.py'
        )
    logger.info('Plugin loaded: %s', name)
    return factory(**resources)

def _resolve_dependencies(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def visit(name: str, stack: set[str]) -> None:
        if name in seen:
            return
        if name in stack:
            chain = ' -> '.join(list(stack) + [name])
            _abort(f'Plugin cyclic dependency: {chain}')
        stack.add(name)
        mod = _import_plugin(name)
        for dep in getattr(mod, 'REQUIRES_PLUGINS', []):
            visit(dep, stack)
        stack.discard(name)
        seen.add(name)
        out.append(name)

    for n in names:
        visit(n, set())
    return out

def _check_conflicts(names: list[str]) -> None:
    active = set(names)
    for n in names:
        mod = _import_plugin(n)
        conflicts = getattr(mod, 'CONFLICTS', [])
        hit = active.intersection(conflicts)
        if hit:
            _abort(
                f'Plugin "{n}" conflicts with: {", ".join(sorted(hit))}'
            )

def _auto_detect_audio(input_ids: list[str]) -> list[str] | None:

    try:
        from process.component.audio.path import auto_detect_audio_path
    except ImportError:
        return None
    found = [auto_detect_audio_path(iid) or '' for iid in input_ids]
    return found if any(found) else None

def load_plugins(
    names_csv: str | None,
    resources: dict | None = None,
    input_ids: list[str] | None = None,
) -> list[object]:
    names = [
        n.strip() for n in (names_csv or '').split(',') if n.strip()
    ]
    names = [_PLUGIN_ALIASES.get(n, n) for n in names]
    blocked = sorted({n for n in names if n in _COMPONENT_PLUGINS})
    if blocked:
        _abort(
            f'Built-in component(s) cannot be selected via -p: '
            f'{", ".join(blocked)} (audio loads automatically with '
            f'audio input; components are consumed by plugins)'
        )
    resources = resources or {}

    if not resources.get('audio') and input_ids and not IGNORE_AUDIO_INPUT:
        auto = _auto_detect_audio(input_ids)
        if auto:
            resources = {**resources, 'audio': auto}
    if resources.get('audio') and 'audio' not in names:

        names = names + ['audio']
    if not names:
        return []
    resolved = _resolve_dependencies(names)
    _check_conflicts(resolved)
    added = [n for n in resolved if n not in names]
    if added:
        logger.info(
            'Auto-resolved plugin dependencies: %s', ','.join(added)
        )
    final: list[str] = []
    for n in resolved:
        reps = names.count(n) if n in names else 1
        final.extend([n] * reps)
    return [load_plugin(n, resources) for n in final]

__all__ = ['load_plugin', 'load_plugins', 'list_plugins']
