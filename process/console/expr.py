import ast
import logging
import re

from process.console.exprlib import scalar_namespace
from process.console.uservars import resolve_into, user_var_exprs

logger = logging.getLogger(__name__)

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)
_IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

_BINDABLE_NAMES = ('random', 'spring')

class UnsafeExpr(ValueError):
    pass

_EXPR_ERRORS = (UnsafeExpr, SyntaxError, ArithmeticError, TypeError,
                ValueError)

def _active_object_key(window) -> tuple:

    ctrl = getattr(window, '_input_transform', None)
    sel = getattr(ctrl, 'selected_id', None) if ctrl is not None else None
    return ('object', sel) if sel is not None else ('global',)

class _RandomExprCallable:

    def __init__(self, window) -> None:
        self._window = window
        self._suffix: tuple = ()

    def bind(self, *key: object) -> None:
        self._suffix = key

    def __call__(self, x: float) -> float:
        from process.component.random.engine import random_eval
        comp = getattr(self._window, '_random_component', None)
        if comp is None:
            return 0.0
        base = _active_object_key(self._window)
        return random_eval(comp, float(x), (*base, *self._suffix))

class _WiggleExprCallable:

    def __init__(self, window) -> None:
        self._window = window

    def __call__(self, x: float) -> float:
        applier = getattr(self._window, '_attr_random', None)
        cur = getattr(applier, 'current_output', None)
        if not callable(cur):
            return 0.0
        return float(cur()) * float(x)

class _TimeExprCallable:

    def __init__(self, window) -> None:
        self._window = window

    def __call__(self, x: float) -> float:
        from process.component.time.engine import time_eval
        comp = getattr(self._window, '_time_component', None)
        if comp is None:
            return 0.0
        tick = getattr(self._window, '_anim_tick', 0)
        return time_eval(comp, float(x), tick)

class _SpringExprCallable:

    def __init__(self, window) -> None:
        self._window = window
        self._suffix: tuple = ()

    def bind(self, *key: object) -> None:
        self._suffix = key

    def __call__(
        self, target: float, freq: float | None = None,
        damping: float | None = None,
    ) -> float:
        from process.component.spring.advance import spring_eval
        comp = getattr(self._window, '_spring_component', None)
        if comp is None:
            return float(target)
        tick = int(getattr(self._window, '_anim_tick', 0) or 0)
        base = _active_object_key(self._window)
        return spring_eval(
            comp, float(target), tick, (*base, *self._suffix), freq, damping)

def bind_random(ns: dict, *key: object) -> None:
    for name in _BINDABLE_NAMES:
        fn = ns.get(name)
        if hasattr(fn, 'bind'):
            fn.bind(*key)

def _eval_node(node: ast.AST, ns: dict) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, ns)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(
                node.value, (int, float)):
            raise UnsafeExpr(f'non-numeric constant: {node.value!r}')
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in ns:
            raise UnsafeExpr(f'name not in namespace: {node.id}')
        value = ns[node.id]
        if callable(value):
            raise UnsafeExpr(f'callable used as value: {node.id}')
        return float(value)
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise UnsafeExpr(f'op not allowed: {type(node.op).__name__}')
        left = _eval_node(node.left, ns)
        right = _eval_node(node.right, ns)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        return left / right
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARYOPS):
            raise UnsafeExpr(f'unary not allowed: {type(node.op).__name__}')
        operand = _eval_node(node.operand, ns)
        return +operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise UnsafeExpr('only bare-name calls allowed')
        fn = ns.get(node.func.id)
        if not callable(fn):
            raise UnsafeExpr(f'not a callable: {node.func.id}')
        args = [_eval_node(a, ns) for a in node.args]
        return float(fn(*args))
    raise UnsafeExpr(f'node not allowed: {type(node).__name__}')

def safe_eval(expr: str, ns: dict) -> float:
    tree = ast.parse(expr, mode='eval')
    return _eval_node(tree, ns)

def rand_namespace(window) -> dict:
    ns: dict = scalar_namespace(window)
    for c in getattr(window, '_console_contributors', None) or []:
        key = getattr(c, 'console_key', None)
        snap = getattr(c, 'snapshot', None)
        if not (key and callable(snap)):
            continue
        for name, value in snap().items():
            if isinstance(value, (int, float)) and not isinstance(
                    value, bool):
                ns[f'{key}_{name}'] = float(value)
    applier = getattr(window, '_attr_random', None)
    values = getattr(applier, 'value_namespace', None)
    if callable(values):
        for name, value in values().items():
            ns[name] = float(value)
    if callable(getattr(applier, 'current_output', None)):
        ns['wiggle'] = _WiggleExprCallable(window)
    _merge_audio_namespace(window, ns)
    if getattr(window, '_random_component', None) is not None:
        ns['random'] = _RandomExprCallable(window)
    if getattr(window, '_time_component', None) is not None:
        ns['time'] = _TimeExprCallable(window)
    if getattr(window, '_spring_component', None) is not None:
        ns['spring'] = _SpringExprCallable(window)

    resolve_into(ns, user_var_exprs(window), safe_eval, _EXPR_ERRORS)
    return ns

def _merge_audio_namespace(window, ns: dict) -> None:

    src = getattr(window, '_audio_source', None)
    mags = getattr(src, 'magnitudes', None)
    if not callable(mags):
        return
    arr = [float(v) for v in mags()]
    n = len(arr)
    if n == 0:
        return
    for i, value in enumerate(arr):
        ns[f'audio_band{i}'] = value
    lo, hi = n // 3, 2 * n // 3
    ns['audio_low'] = sum(arr[:lo or 1]) / (lo or 1)
    ns['audio_mid'] = sum(arr[lo:hi]) / max(1, hi - lo)
    ns['audio_high'] = sum(arr[hi:]) / max(1, n - hi)

def _has_token(value: str, ns: dict) -> bool:

    stripped = value.strip()
    if stripped in ns and callable(ns[stripped]):
        return False
    return any(name in ns for name in _IDENT_RE.findall(value))

def _is_vector_expr(value: object, ns: dict) -> bool:

    return (isinstance(value, (list, tuple)) and any(
        isinstance(el, str) and _has_token(el, ns) for el in value))

def resolve_vector(value: list, ns: dict) -> list:
    out: list = []
    for el in value:
        out.append(safe_eval(el, ns) if isinstance(el, str) else float(el))
    return out

def split_expressions(constants: dict, ns: dict) -> dict:
    if not ns:
        return {}
    out: dict = {}
    for key, value in constants.items():
        if key.startswith('_'):
            continue
        if isinstance(value, str) and _has_token(value, ns):
            out[key] = value
        elif _is_vector_expr(value, ns):
            out[key] = value
    return out

def resolve_constants(constants: dict, ns: dict) -> dict:
    if not ns:
        return constants
    resolved: dict = {}
    for key, value in constants.items():
        if key.startswith('_'):
            resolved[key] = value
            continue
        is_scalar = isinstance(value, str) and _has_token(value, ns)
        is_vector = _is_vector_expr(value, ns)
        if not (is_scalar or is_vector):
            resolved[key] = value
            continue
        try:
            bind_random(ns, key)
            resolved[key] = (resolve_vector(value, ns) if is_vector
                             else safe_eval(value, ns))
        except SyntaxError:

            logger.debug(
                'Rand expr incomplete (transient edit): %s=%r', key, value)
        except (UnsafeExpr, ArithmeticError, TypeError) as e:
            logger.warning(
                'Rand expr rejected: %s=%r (%s)', key, value, e)
    return resolved
