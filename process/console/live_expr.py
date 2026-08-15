import logging
import sys

from process.console.expr import (
    UnsafeExpr, bind_random, rand_namespace, resolve_constants,
    resolve_vector, safe_eval, split_expressions)
from process.console.persist import apply_constants, find_settings_module
from process.console.uservars import (
    register_user_vars, split_user_vars)

logger = logging.getLogger(__name__)

def apply_expr_constants(window, plugin, settings_path: str, raw: dict):

    constants, user_vars = split_user_vars(
        raw, find_settings_module(settings_path),
        _vector_const_names(plugin))
    register_user_vars(window, settings_path, user_vars)
    ns = rand_namespace(window)
    register_bindings(
        window, plugin, settings_path, split_expressions(constants, ns))
    resolved = resolve_constants(constants, ns)
    _apply_vector_constants(plugin, resolved)
    return apply_constants(settings_path, resolved)

def _vector_const_names(plugin) -> set:

    mapper = getattr(plugin, 'expr_vector_attr_map', None)
    return set(mapper()) if callable(mapper) else set()

def _apply_vector_constants(plugin, resolved: dict) -> None:

    getter = getattr(plugin, 'expr_vector_system', None)
    mapper = getattr(plugin, 'expr_vector_attr_map', None)
    if not (callable(getter) and callable(mapper)):
        return
    system = getter()
    if system is None:
        return
    amap = mapper()
    for const, target in amap.items():
        vec = _as_float_vec(resolved.get(const))
        if vec is not None:
            setattr(system, target[0], vec)

def _as_float_vec(value: object) -> list | None:

    if not isinstance(value, (list, tuple)):
        return None
    out: list = []
    for el in value:
        if isinstance(el, bool) or not isinstance(el, (int, float)):
            return None
        out.append(float(el))
    return out

def inject_expr_text(window, settings_path: str, constants: dict) -> None:
    for const, expr in binding_exprs(window, settings_path).items():
        if const in constants:
            constants[const] = expr

def register_bindings(
    window, plugin, settings_path: str, exprs: dict,
) -> None:
    key = str(settings_path)
    registry = getattr(window, '_expr_bindings', None)
    if registry is None:
        registry = {}
        window._expr_bindings = registry
    if exprs:
        registry[key] = {'plugin': plugin, 'exprs': dict(exprs)}
    else:
        registry.pop(key, None)
    _ensure_processor(window)

def binding_exprs(window, settings_path: str) -> dict:
    registry = getattr(window, '_expr_bindings', None) or {}
    entry = registry.get(str(settings_path))
    return dict(entry['exprs']) if entry else {}

def _ensure_processor(window) -> None:
    if getattr(window, '_expr_proc_installed', False):
        return
    procs = getattr(window, '_frame_processors', None)
    if procs is None:
        return
    procs.insert(min(1, len(procs)), _make_processor(window))
    window._expr_proc_installed = True

def _make_processor(window):
    def _proc(splat):
        _apply_live(window)
        return splat
    return _proc

def _apply_live(window) -> None:
    registry = getattr(window, '_expr_bindings', None)
    if not registry:
        return
    ns = rand_namespace(window)
    if not ns:
        return
    for entry in registry.values():
        _apply_entry(entry, ns)

def _apply_entry(entry: dict, ns: dict) -> None:
    exprs = entry['exprs']
    vsys, vmap = _vector_target(entry)
    system = getattr(entry['plugin'], 'system', None)
    if system is not None:
        amap = entry.get('attr_map')
        if amap is None:
            amap = _resolve_attr_map(system, exprs, set(vmap or ()))
            entry['attr_map'] = amap
        _apply_targets(system, amap, exprs, ns)
    if vsys is not None:
        _apply_targets(vsys, vmap, exprs, ns)

def _apply_targets(system, amap: dict, exprs: dict, ns: dict) -> None:

    for const, expr in exprs.items():
        target = amap.get(const)
        if target is None:
            continue
        attr, is_int = target
        try:
            bind_random(ns, const)
            if isinstance(expr, (list, tuple)):
                setattr(system, attr, resolve_vector(expr, ns))
            else:
                value = safe_eval(expr, ns)
                setattr(system, attr,
                        int(round(value)) if is_int else value)
        except (UnsafeExpr, SyntaxError, ArithmeticError, TypeError):
            continue

def _vector_target(entry: dict) -> tuple:

    cached = entry.get('_vec_target')
    if cached is not None:
        return cached
    plugin = entry['plugin']
    getter = getattr(plugin, 'expr_vector_system', None)
    mapper = getattr(plugin, 'expr_vector_attr_map', None)
    if not (callable(getter) and callable(mapper)):
        entry['_vec_target'] = (None, None)
        return None, None
    result = (getter(), mapper())
    entry['_vec_target'] = result
    return result

def _resolve_attr_map(system, exprs: dict, vec_handled=frozenset()) -> dict:
    module = sys.modules.get(type(system).__module__)
    default_map = getattr(module, '_DEFAULT_MAP', None) or {}
    ints = set(getattr(module, '_DEFAULT_INTS', ()) or ())
    vec_map = getattr(module, '_DEFAULT_VEC_MAP', None) or {}
    const_to_attr = {const: attr for attr, const in default_map.items()}
    const_to_vec = {const: attr for attr, const in vec_map.items()}
    out: dict = {}
    for const in exprs:
        attr = const_to_attr.get(const)
        if attr is not None:
            out[const] = (attr, attr in ints)
            continue
        vattr = const_to_vec.get(const)
        if vattr is not None:
            out[const] = (vattr, False)
    _warn_unmapped(module, exprs, out, vec_handled)
    return out

def _warn_unmapped(
    module, exprs: dict, mapped: dict, vec_handled=frozenset(),
) -> None:

    missing = sorted(set(exprs) - set(mapped) - set(vec_handled))
    if not missing:
        return
    logger.warning(
        'EXPR_NO_LIVE_TARGET: %s has no live attribute in %s - the '
        'expression is evaluated once on apply and will not animate '
        'per frame', ', '.join(missing),
        getattr(module, '__name__', '?'))
