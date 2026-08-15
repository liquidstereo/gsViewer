import ast
import json
import logging
from pathlib import Path
from types import ModuleType

from process.console.reload import _find_module_for_path, _propagate
from process.common.floatfmt import dumps_fixed, fixed_repr

logger = logging.getLogger(__name__)

def ensure_json_suffix(path: str) -> str:
    if not path:
        return path
    return str(Path(path).with_suffix('.json'))

def _is_jsonable(value) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_jsonable(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(k, str) and _is_jsonable(v)
            for k, v in value.items()
        )
    return False

def _coerce(current, value):
    if isinstance(current, tuple) and isinstance(value, list):
        if len(current) == len(value):
            return tuple(_coerce(c, v) for c, v in zip(current, value))
        return tuple(value)
    return value

def _type_mismatch(current, value) -> bool:
    return (isinstance(current, (int, float))
            and not isinstance(current, bool)
            and isinstance(value, str))

def _module_assigned_names(module: ModuleType) -> set | None:
    path = getattr(module, '__file__', None)
    if not path:
        return None
    try:
        tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    except (OSError, SyntaxError):
        return None
    names: set = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
    return names

def collect_constants(module: ModuleType) -> dict:
    assigned = _module_assigned_names(module)
    result = {}
    for key, value in vars(module).items():
        if key.startswith('_') or not key.isupper():
            continue
        if assigned is not None and key not in assigned:
            continue
        if _is_jsonable(value):
            result[key] = value
    return result

def find_settings_module(settings_path: str) -> ModuleType | None:
    return _find_module_for_path(settings_path)

def apply_constants(
    settings_path: str, constants: dict,
) -> ModuleType | None:
    if not constants:
        return None
    module = _find_module_for_path(settings_path)
    if module is None:
        return None
    applied = {}
    for key, value in constants.items():
        if not hasattr(module, key):
            continue
        current = getattr(module, key)
        if _type_mismatch(current, value):
            logger.warning('Skip type-mismatched override: %s=%r', key, value)
            continue
        coerced = _coerce(current, value)
        setattr(module, key, coerced)
        applied[key] = coerced
    if not applied:
        return None
    _propagate(module, applied)
    logger.info(
        'Override constants applied: %s (%d)',
        Path(settings_path).name, len(applied),
    )
    return module

def _assign_name(node) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None

def _const_literal(value) -> str | None:
    if value is None:
        return 'None'
    if isinstance(value, bool):
        return 'True' if value else 'False'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return fixed_repr(value)
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (list, tuple)):
        parts = [_const_literal(item) for item in value]
        if any(part is None for part in parts):
            return None
        inner = ', '.join(parts)
        if isinstance(value, tuple):
            return f'({inner},)' if len(parts) == 1 else f'({inner})'
        return f'[{inner}]'
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            key_lit = _const_literal(k) if isinstance(k, str) else None
            val_lit = _const_literal(v)
            if key_lit is None or val_lit is None:
                return None
            parts.append(f'{key_lit}: {val_lit}')
        return '{' + ', '.join(parts) + '}'
    return None

def write_constants_to_settings(settings_path: str, constants: dict) -> int:
    try:
        src = Path(settings_path).read_text(encoding='utf-8')
        tree = ast.parse(src)
    except (OSError, SyntaxError) as e:
        logger.warning('Set-as-default read/parse failed: %s', e)
        return 0
    starts = []
    off = 0
    for line in src.splitlines(keepends=True):
        starts.append(off)
        off += len(line)
    edits = []
    for node in tree.body:
        name = _assign_name(node)
        if name is None or name not in constants:
            continue
        v = node.value
        start = starts[v.lineno - 1] + v.col_offset
        end = starts[v.end_lineno - 1] + v.end_col_offset

        ls = start
        while ls > 0 and src[ls - 1] in ' \t\r\n':
            ls -= 1
        le = end
        while le < len(src) and src[le] in ' \t\r\n':
            le += 1
        if ls > 0 and src[ls - 1] == '(' and le < len(src) and src[le] == ')':
            start, end = ls - 1, le + 1
        cur = src[start:end]
        try:
            cur_val = ast.literal_eval(cur)
        except (ValueError, SyntaxError):
            continue
        if cur_val == constants[name]:
            continue
        literal = _const_literal(constants[name])
        if literal is None or literal == cur:
            continue
        edits.append((start, end, literal))
    if not edits:
        return 0
    for start, end, literal in sorted(edits, reverse=True):
        src = src[:start] + literal + src[end:]
    try:
        Path(settings_path).write_text(src, encoding='utf-8')
    except OSError as e:
        logger.warning('Set-as-default write failed: %s', e)
        return 0
    logger.info('Set-as-default: %d constant(s) written to %s',
                len(edits), Path(settings_path).name)
    return len(edits)

def load_override_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning('Override load failed: %s', e)
        return {}
    return data if isinstance(data, dict) else {}

def save_override_file(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            dumps_fixed(data, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
    except OSError as e:
        logger.warning('Override save failed: %s', e)
        return
    n_c = len(data.get('constants', {}))
    n_a = len(data.get('attrs', {}))
    logger.info(
        'Override saved: %s (constants=%d attrs=%d)', path.name, n_c, n_a,
    )
