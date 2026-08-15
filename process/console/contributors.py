def _is_own_contributor(contributor, skip_plugin) -> bool:

    if skip_plugin is None:
        return False
    own = getattr(skip_plugin, 'system', None)
    return own is not None and getattr(contributor, 'system', None) is own

def merge_contributor_snapshots(window, data: dict, skip_plugin=None) -> None:
    for c in getattr(window, '_console_contributors', None) or []:
        if _is_own_contributor(c, skip_plugin):
            continue
        key = getattr(c, 'console_key', None)
        snap = getattr(c, 'snapshot', None)
        if key and callable(snap):
            data[key] = snap()

def apply_contributor_sections(window, data: dict, skip_plugin=None) -> bool:
    applied = False
    for c in getattr(window, '_console_contributors', None) or []:
        if _is_own_contributor(c, skip_plugin):
            continue
        key = getattr(c, 'console_key', None)
        apply = getattr(c, 'apply', None)
        if key and callable(apply) and isinstance(data.get(key), dict):
            apply(data[key])
            applied = True
    return applied
