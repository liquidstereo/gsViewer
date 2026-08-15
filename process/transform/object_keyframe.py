import logging

import numpy as np

from configs.settings import ENABLE_INSTANT_JSON_SYNC
from configs.settings_annot import (
    ANNOT_ANIM_DURATION, ANNOT_ANIM_EASING, ANNOT_ANIM_FPS,
)
from process.annotation.markers import compute_annotation_markers
from process.common.core import display_name, json_root_path
from process.common.widget import request_repaint
from process.keyframe import (
    KeyframeAnimator, KeyframeSequence, prompt_keyframe,
    read_keyframe_json, write_keyframe_json,
)
from process.undo import record_keyframe_seq
from process.widget.text_case import keep_case

logger = logging.getLogger(__name__)

def _reorthogonalize(R: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(R)
    R2 = u @ vt
    if np.linalg.det(R2) < 0.0:
        u[:, -1] *= -1.0
        R2 = u @ vt
    return R2.astype(np.float32)

def _to_json(item: dict) -> dict:
    return {
        'center':   item['center'].tolist(),
        'size':     item['size'].tolist(),
        'rotation': item['rotation'].tolist(),
        'label':    item['label'],
        'duration': int(item.get('duration', 0)),
    }

def _from_json(d: dict) -> dict:
    return {
        'center':   np.array(d['center'], dtype=np.float32),
        'size':     np.array(d['size'], dtype=np.float32),
        'rotation': np.array(d['rotation'], dtype=np.float32),
        'label':    d['label'],
        'duration': int(d.get('duration', 0)),
    }

class ObjectKeyframeStore:

    def __init__(self, window) -> None:
        self._window = window
        self._seqs: dict[str, KeyframeSequence] = {}
        self._active_id: str | None = None
        name = getattr(window, '_json_key', '') or 'default'
        self._path = json_root_path(name, 'object.json')
        self.animator = KeyframeAnimator(
            window, self._capture, self._apply, self._interpolate,
            ANNOT_ANIM_DURATION, ANNOT_ANIM_FPS, ANNOT_ANIM_EASING,
        )
        self.load()

    def seq(self, input_id: str) -> KeyframeSequence:
        s = self._seqs.get(input_id)
        if s is None:
            s = KeyframeSequence(_to_json, _from_json)
            self._seqs[input_id] = s
        return s

    def set_active(self, input_id: str) -> None:
        self._active_id = input_id

    def clear(self) -> None:
        self._seqs.clear()
        self._active_id = None

    def _controller(self):
        return getattr(self._window, '_input_transform', None)

    def _target(self):
        c = self._controller()
        if c is None or self._active_id is None:
            return None
        return c.targets.get(self._active_id)

    def _capture(self) -> dict | None:
        t = self._target()
        if t is None:
            return None
        return {
            'center':   t.center.astype(np.float32).copy(),
            'size':     t.size.astype(np.float32).copy(),
            'rotation': t.rotation.astype(np.float32).copy(),
        }

    def _apply(self, state: dict) -> None:
        t = self._target()
        if t is None:
            return
        t.center = state['center']
        t.size = state['size']
        t.rotation = state['rotation']
        request_repaint(self._window)

    @staticmethod
    def _interpolate(src: dict, dst: dict, t: float) -> dict:
        inv = 1.0 - t
        R = src['rotation'] * inv + dst['rotation'] * t
        return {
            'center':   (src['center'] * inv + dst['center'] * t).astype(
                np.float32),
            'size':     (src['size'] * inv + dst['size'] * t).astype(
                np.float32),
            'rotation': _reorthogonalize(R),
        }

    def save(self) -> None:
        data = {
            iid: s.to_list()
            for iid, s in self._seqs.items() if s.count() > 0
        }
        write_keyframe_json(self._path, data, 'Object', logger)

    def load(self) -> None:
        data = read_keyframe_json(self._path, 'Object', logger)
        if data is None:
            return
        for iid, items in data.items():
            self.seq(iid).from_list(items)
        logger.info('Object keyframes loaded: %s', self._path.name)

def _store(win):
    return getattr(win, '_object_keyframes', None)

def _resolve_id(c) -> str | None:

    if c.selected_id is not None:
        return c.selected_id
    ids = list(c.targets.keys())
    return ids[0] if len(ids) == 1 else None

def _selected(win):
    c = getattr(win, '_input_transform', None)
    if c is None:
        return None, None, None
    sel = _resolve_id(c)
    if sel is None:
        return c, None, None
    return c, sel, c.targets.get(sel)

def _overlay(win, message: str) -> None:
    win._message_overlay = message
    win._message_overlay_timer.start()

def _notify_no_selection(win, c) -> None:

    n = len(c.targets) if c is not None else 0
    if n > 1:
        _overlay(win, 'Select an object for keyframe')
        return
    logger.warning('No object available for keyframe')

def handle_add_object_keyframe(win) -> None:
    store = _store(win)
    c, sel, target = _selected(win)
    if store is None:
        return
    if target is None:
        _notify_no_selection(win, c)
        return
    seq = store.seq(sel)
    name = display_name(win, sel)
    first = seq.count() == 0
    default = f'{name} Keyframe {seq.count() + 1}'
    label, duration, ok = prompt_keyframe(
        win, 'Add Object Keyframe', default,
        store.animator.duration_ms, first,
    )
    if not ok or not label:
        return
    before = seq.snapshot()
    seq.add({
        'center':   target.center.astype(np.float32).copy(),
        'size':     target.size.astype(np.float32).copy(),
        'rotation': target.rotation.astype(np.float32).copy(),
        'label':    label,
        'duration': duration,
    })
    seq.set_cursor(seq.count() - 1)
    if ENABLE_INSTANT_JSON_SYNC:
        store.save()
    record_keyframe_seq(
        win, store, seq, before, seq.snapshot(), f'Add {name} keyframe',
    )
    _overlay(win, f'{keep_case(name)} Keyframe Added: {keep_case(label)}')
    request_repaint(win)

def handle_remove_object_keyframe(win) -> None:
    store = _store(win)
    c, sel, target = _selected(win)
    if store is None:
        return
    if sel is None:
        _notify_no_selection(win, c)
        return
    seq = store.seq(sel)
    before = seq.snapshot()
    if seq.remove_last():
        if ENABLE_INSTANT_JSON_SYNC:
            store.save()
        record_keyframe_seq(
            win, store, seq, before, seq.snapshot(),
            f'Remove {display_name(win, sel)} keyframe',
        )
        _overlay(win, f'{keep_case(display_name(win, sel))} KEY Removed.')
        request_repaint(win)
    else:
        logger.warning('No object keyframes to remove')

def handle_clear_object_keyframes(win) -> None:
    store = _store(win)
    c, sel, target = _selected(win)
    if store is None:
        return
    if sel is None:
        _notify_no_selection(win, c)
        return
    seq = store.seq(sel)
    if seq.count() == 0:
        logger.warning('No object keyframes to clear')
        return
    store.animator.stop()
    before = seq.snapshot()
    seq.clear()
    if ENABLE_INSTANT_JSON_SYNC:
        store.save()
    record_keyframe_seq(
        win, store, seq, before, seq.snapshot(),
        f'Clear {display_name(win, sel)} keyframes',
    )
    _overlay(win, f'{keep_case(display_name(win, sel))} KEYS Cleared.')
    request_repaint(win)

def _goto(win, delta: int) -> None:
    store = _store(win)
    c, sel, target = _selected(win)
    if store is None:
        return
    if sel is None:
        _notify_no_selection(win, c)
        return
    seq = store.seq(sel)
    item = seq.goto(delta)
    if item is None:
        return
    store.set_active(sel)
    store.animator.start(item)
    n = seq.count()
    _overlay(
        win,
        f'{keep_case(display_name(win, sel))} KEY '
        f'[{seq.cursor() + 1}/{n}]: {keep_case(item["label"])}',
    )

def handle_goto_next_object_keyframe(win) -> None:
    _goto(win, 1)

def handle_goto_prev_object_keyframe(win) -> None:
    _goto(win, -1)

def handle_toggle_object_keyframes(win) -> None:
    win._show_object_kf = not getattr(win, '_show_object_kf', True)
    state = 'On' if win._show_object_kf else 'Off'
    _overlay(win, f'Object Markers {state}.')
    logger.info('Object keyframe markers visible: %s', win._show_object_kf)
    request_repaint(win)

def compute_selected_object_markers(
    win, viewmat, K, ortho: bool = False,
) -> list[tuple[int, int, str]]:
    if not getattr(win, '_show_object_kf', True):
        return []
    store = _store(win)
    _c, sel, _t = _selected(win)
    if store is None or sel is None:
        return []
    seq = store.seq(sel)
    if seq.count() == 0:
        return []
    items = [
        {'pos': it['center'], 'label': it['label']}
        for it in seq.items()
    ]
    return compute_annotation_markers(items, viewmat, K, ortho=ortho)
