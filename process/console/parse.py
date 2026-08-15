import json
import logging

logger = logging.getLogger(__name__)

def _retry_lenient(source: str) -> dict | None:
    try:
        cooked = _strip_trailing_commas(_quote_bare_values(source))
        return json.loads(cooked)
    except json.JSONDecodeError as e:
        logger.warning('Console JSON parse skipped: %s', e)
        return None

def _strip_trailing_commas(text: str) -> str:
    out = list(text)
    n = len(out)
    in_str = False
    esc = False
    for i, ch in enumerate(out):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == ',':
            j = i + 1
            while j < n and out[j] in ' \t\r\n':
                j += 1
            if j < n and out[j] in ']}':
                out[i] = ''
    return ''.join(out)

def _quote_bare_values(source: str) -> str:
    out: list = []
    i, n = 0, len(source)
    ctx: list = []
    expect_value = True
    while i < n:
        ch = source[i]
        if ch in ' \t\r\n':
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            end = _scan_string(source, i)
            out.append(source[i:end])
            i = end
            expect_value = False
            continue
        if ch == '{':
            out.append(ch)
            ctx.append('obj')
            i += 1
            expect_value = False
            continue
        if ch == '[':
            out.append(ch)
            ctx.append('arr')
            i += 1
            expect_value = True
            continue
        if ch in '}]':
            out.append(ch)
            if ctx:
                ctx.pop()
            i += 1
            expect_value = False
            continue
        if ch == ':':
            out.append(ch)
            i += 1
            expect_value = True
            continue
        if ch == ',':
            out.append(ch)
            i += 1
            expect_value = bool(ctx) and ctx[-1] == 'arr'
            continue
        if expect_value:
            end = _read_bare_token(source, i)
            out.append(_quote_bare_elem(source[i:end].strip()))
            i = end
            expect_value = False
            continue
        out.append(ch)
        i += 1
    return ''.join(out)

def _scan_string(source: str, i: int) -> int:

    n = len(source)
    i += 1
    esc = False
    while i < n:
        ch = source[i]
        if esc:
            esc = False
        elif ch == '\\':
            esc = True
        elif ch == '"':
            return i + 1
        i += 1
    return i

def _read_bare_token(source: str, i: int) -> int:

    n = len(source)
    depth = 0
    in_str = False
    esc = False
    while i < n:
        ch = source[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch in '([{':
            depth += 1
            i += 1
            continue
        if ch in ')]}':
            if depth == 0:
                break
            depth -= 1
            i += 1
            continue
        if ch == ',' and depth == 0:
            break
        i += 1
    return i

def _quote_bare_elem(elem: str) -> str:

    s = elem.strip()
    if not s or s[0] in '{[':
        return s
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        return json.dumps(s)
