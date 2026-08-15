from typing import Callable

from configs.settings_overlay import TEXT_OVERLAY_CASE

_KEEP_MARK: str = '\x00'

_CASE_TRANSFORMS: dict[str, Callable[[str], str]] = {
    'DEFAULT':    lambda s: s,
    'CAPITALIZE': lambda s: s,
    'UPPER':      str.upper,
    'LOWER':      str.lower,
    'TITLE':      str.title,
    'SWAP':       str.swapcase,
}

def keep_case(s: str) -> str:
    if not s:
        return s
    return f'{_KEEP_MARK}{s}{_KEEP_MARK}'

def strip_keep_case(text: str) -> str:
    if not text or _KEEP_MARK not in text:
        return text
    return text.replace(_KEEP_MARK, '')

def apply_overlay_case(text: str) -> str:
    if not text:
        return text
    fn = _CASE_TRANSFORMS.get(
        TEXT_OVERLAY_CASE, _CASE_TRANSFORMS['DEFAULT'],
    )
    if _KEEP_MARK not in text:
        return fn(text.capitalize())

    parts = text.split(_KEEP_MARK)
    out: list[str] = []
    for i, p in enumerate(parts):
        if not p:
            out.append(p)
            continue
        if i % 2 == 0:
            out.append(fn(p.capitalize()))
        else:
            out.append(p)
    return ''.join(out)
