from collections.abc import Callable

_ATTR_EXTRA_KEY = '_attr_extra_specs'

def compose_specs(*items) -> list:
    out: list = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, (list, tuple)):
            out.extend(compose_specs(*item))
            continue
        out.append(item)
    return out

def spec_when(pred: Callable[[], bool], spec) -> list:
    if not pred():
        return []
    return compose_specs(spec() if callable(spec) else spec)

def register_extra_specs(
    window, key: str, provider: Callable[[], list],
) -> None:
    table = getattr(window, _ATTR_EXTRA_KEY, None)
    if table is None:
        table = {}
        setattr(window, _ATTR_EXTRA_KEY, table)
    providers = table.setdefault(key, [])
    if provider not in providers:
        providers.append(provider)

def unregister_extra_specs(
    window, key: str, provider: Callable[[], list],
) -> None:
    table = getattr(window, _ATTR_EXTRA_KEY, None)
    if not table:
        return
    providers = table.get(key)
    if not providers or provider not in providers:
        return
    providers.remove(provider)

def extra_specs(window, key: str) -> list:
    table = getattr(window, _ATTR_EXTRA_KEY, None)
    if not table:
        return []
    return compose_specs(*[p() for p in table.get(key, [])])
