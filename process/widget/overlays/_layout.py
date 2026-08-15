from process.common.font import make_font
from configs.settings_overlay import (
    OVERLAY_MARGIN, AUDIO_LIST_TITLE, MESSAGE_OVERLAY_MAX_CHARS,
    OVERLAY_LINE_PAD, OVERLAY_LINEBREAK, OVERLAY_SEPARATOR_CHAR,
    OVERLAY_TEXT_BOLD, OVERLAY_TEXT_ITALIC, OVERLAY_TEXT_LINEHEIGHT,
    OVERLAY_TOP_LEFT_ORDER, REGION_LIST_ITEM_PREFIX,
    REGION_LIST_ITEM_PREFIX_SELECTED, REGION_LIST_TITLE,
)
from process.widget.scale import scaled_margin, scaled_text_size
from process.widget.text_case import strip_keep_case

SEPARATOR: str = OVERLAY_SEPARATOR_CHAR

_HEADER_KEYS: tuple = ('info', 'stat', 'cam', 'objinfo')
_HEADER_ORDER: tuple = tuple(
    k for k in OVERLAY_TOP_LEFT_ORDER if k in _HEADER_KEYS
)

ROLE_TEXT: str = 'text'
ROLE_SEP: str = 'sep'
ROLE_REGION_HEAD: str = 'region_head'
ROLE_REGION_ITEM: str = 'region_item'
ROLE_OBJECT_HEAD: str = 'object_head'
ROLE_OBJECT_ITEM: str = 'object_item'
ROLE_AUDIO_HEAD: str = 'audio_head'
ROLE_AUDIO_ITEM: str = 'audio_item'
ROLE_STATUS: str = 'status'
ROLE_STATUS_HEAD: str = 'status_head'
ROLE_MESSAGE: str = 'message'

OBJECT_LIST_TITLE: str = 'OBJECT'

def _text_lines(text: str | None, role: str) -> list:
    out = []
    for line in (text or '').split('\n'):
        if line:
            if line.startswith('[TITLE]'):
                out.append({'text': line[7:], 'role': ROLE_STATUS_HEAD, 'index': None})
            else:
                out.append({'text': line, 'role': role, 'index': None})
    return out

def _sep() -> dict:
    return {'text': SEPARATOR, 'role': ROLE_SEP, 'index': None}

def _visible_len(text: str) -> int:

    return len(strip_keep_case(text))

def _wrap_message(text: str, max_chars: int) -> list:
    if _visible_len(text) <= max_chars:
        return [text]
    lines: list = []
    cur = ''
    cur_len = 0
    for word in text.split(' '):
        wlen = _visible_len(word)
        if not cur:
            cur, cur_len = word, wlen
        elif cur_len + 1 + wlen <= max_chars:
            cur = f'{cur} {word}'
            cur_len += 1 + wlen
        else:
            lines.append(cur)
            cur, cur_len = word, wlen
    if cur:
        lines.append(cur)
    return lines

def _list_block(
    items: list | None, title: str, head_role: str, item_role: str,
    suffix: str = '',
) -> list:
    if not items:
        return []

    if item_role == 'object_item' :
        surfix = 'objects'
    else :
        surfix = 'items'
    title_text = (
        f'{title}s ({len(items)} {surfix})' if len(items) > 1 else title
    )

    title_text = f'{title_text}{suffix}'
    block = [{'text': title_text, 'role': head_role, 'index': None}]
    for i, item in enumerate(items):
        selected = bool(item[1]) if len(item) > 1 else False
        prefix = (REGION_LIST_ITEM_PREFIX_SELECTED if selected
                  else REGION_LIST_ITEM_PREFIX)
        if len(item) > 2 and isinstance(item[-1], str):
            tail = item[-1]
        elif len(item) > 7 and item[7]:
            tail = ' (Solo)'
        else:
            tail = ''
        block.append({'text': f'{prefix}{item[0]}{tail}',
                      'role': item_role, 'index': i})
    return block

def _object_active_suffix(object_items: list | None) -> str:
    if not object_items:
        return ''
    solo_label = next(
        (it[0] for it in object_items if len(it) > 7 and it[7]), None,
    )
    if solo_label is not None:
        return f' . Solo: {solo_label}'
    if len(object_items) > 1:
        isolated = any(
            len(it) > 6 and not it[2] and not it[6] for it in object_items
        )
        visible = [it[0] for it in object_items if len(it) > 2 and it[2]]
        nvis = len(visible)
        selected = next(
            (it[0] for it in object_items if len(it) > 1 and it[1]), None,
        )
        if isolated:
            if nvis == 1:
                return f' . Isolate: {visible[0]}'
            return f' . Isolate: {nvis} Objects'
        if selected is not None:
            return f' . Selected: {selected}'

        return ''
    item = object_items[0]
    if len(item) > 1 and item[1]:
        return f' . Selected: {item[0]}'
    points = item[3] if len(item) > 3 else 0
    files = item[4] if len(item) > 4 else 0
    files_tail = f' ({files} Files)' if files > 1 else ''
    return f' . Points: {points:,}{files_tail}'

def object_sole_visible_index(object_items: list | None) -> int | None:
    if not object_items or len(object_items) <= 1:
        return None
    vis = [i for i, it in enumerate(object_items) if len(it) > 2 and it[2]]
    return vis[0] if len(vis) == 1 else None

def build_overlay_lines(
    texts: dict, region_items: list | None = None,
    object_items: list | None = None, message: str = '',
    audio_items: list | None = None,
) -> list:
    multi = bool(object_items)
    header_keys = (
        tuple(k for k in _HEADER_ORDER if k != 'objinfo')
        if multi else _HEADER_ORDER
    )
    header: list = []
    for key in header_keys:
        header.extend(_text_lines(texts.get(key), ROLE_TEXT))
    objects = _list_block(
        object_items, OBJECT_LIST_TITLE, ROLE_OBJECT_HEAD, ROLE_OBJECT_ITEM,
        suffix=_object_active_suffix(object_items),
    )
    audio = _list_block(
        audio_items, AUDIO_LIST_TITLE, ROLE_AUDIO_HEAD, ROLE_AUDIO_ITEM,
    )
    region = _list_block(
        region_items, REGION_LIST_TITLE, ROLE_REGION_HEAD, ROLE_REGION_ITEM,
    )
    status = _text_lines(texts.get('status'), ROLE_STATUS)

    lines: list = []
    if header:
        lines.extend(header)

    lines.append(_sep())

    prior = False
    if multi:
        lines.extend(objects)
        prior = True
    if audio_items:
        if prior:
            lines.append(_sep())
        lines.extend(audio)
        prior = True
    if region_items:
        if prior:
            lines.append(_sep())
        lines.extend(region)
        prior = True
    if status:
        if prior:
            lines.append(_sep())
        lines.extend(status)

    if message:
        if lines and lines[-1]['role'] != ROLE_SEP:
            lines.append(_sep())
        for mline in _wrap_message(message, MESSAGE_OVERLAY_MAX_CHARS):
            lines.append(
                {'text': mline, 'role': ROLE_MESSAGE, 'index': None}
            )
    return lines

def line_metrics(painter, w: int) -> tuple:
    text_size = scaled_text_size(w)
    f = make_font()
    f.setPointSize(text_size)
    f.setBold(OVERLAY_TEXT_BOLD)
    f.setItalic(OVERLAY_TEXT_ITALIC)
    painter.save()
    painter.setFont(f)
    fm = painter.fontMetrics()
    painter.restore()
    lh = round(fm.height() * OVERLAY_TEXT_LINEHEIGHT) + OVERLAY_LINE_PAD
    pad_top = scaled_margin(w, OVERLAY_MARGIN)
    y0 = fm.ascent() + pad_top
    gap = int(text_size * OVERLAY_LINEBREAK)
    pad_left = scaled_margin(w, OVERLAY_MARGIN)
    return y0, lh, gap, pad_left

def slot_baseline(y0: int, lh: int, gap: int, slot: int) -> int:
    return y0 + lh * slot + gap * slot
