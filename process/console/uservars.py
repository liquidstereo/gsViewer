import logging

logger = logging.getLogger(__name__)

MAX_RESOLVE_PASSES = 8

def split_user_vars(
    constants: dict, module, known=frozenset(),
) -> tuple[dict, dict]:
    settings_c: dict = {}
    user: dict = {}
    for key, value in constants.items():
        if key.startswith('_'):
            settings_c[key] = value
        elif key in known:
            settings_c[key] = value
        elif module is not None and hasattr(module, key):
            settings_c[key] = value
        else:
            user[key] = value
    return settings_c, user

def register_user_vars(window, settings_path: str, user_vars: dict) -> None:
    if window is None:
        return
    registry = getattr(window, '_console_user_vars', None)
    if registry is None:
        registry = {}
        window._console_user_vars = registry
    key = str(settings_path)
    if user_vars:
        registry[key] = dict(user_vars)
    else:
        registry.pop(key, None)

def user_var_exprs(window) -> dict:
    out: dict = {}
    for defs in (getattr(window, '_console_user_vars', None) or {}).values():
        out.update(defs)
    return out

def own_user_vars(window, settings_path: str) -> dict:
    registry = getattr(window, '_console_user_vars', None) or {}
    return dict(registry.get(str(settings_path)) or {})

def resolve_into(
    ns: dict, exprs: dict, evaluate, errors: tuple,
    max_passes: int = MAX_RESOLVE_PASSES,
) -> list:
    pending: dict = {}
    for name, value in exprs.items():
        if name in ns:
            logger.warning(
                'Console user variable ignored (shadows built-in): %s', name)
            continue
        pending[name] = value
    for _ in range(max_passes):
        progressed = False
        for name in list(pending):
            value = pending[name]
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                ns[name] = float(value)
                del pending[name]
                progressed = True
                continue
            try:
                ns[name] = float(evaluate(str(value), ns))
            except errors:
                continue
            del pending[name]
            progressed = True
        if not pending or not progressed:
            break
    if pending:
        logger.warning(
            'Console user variables unresolved (unknown name or cycle): %s',
            ', '.join(sorted(pending)))
    return sorted(pending)
