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
from process.transform import global_region
from process.undo import record_keyframe_seq
from process.widget.text_case import keep_case

logger = logging.getLogger(__name__)

_GLOBAL_JSON = 'object_global.json'

def _snap_to_json(snap: dict) -> dict:
    return {
        iid: {
            'center':   s['center'].tolist(),
            'size':     s['size'].tolist(),
            'rotation': s['rotation'].tolist(),
        }
        for iid, s in snap.items()
    }

def _snap_from_json(data: dict) -> dict:
    return {
        iid: {
            'center':   np.array(s['center'], dtype=np.float32),
            'size':     np.array(s['size'], dtype=np.float32),
            'rotation': np.array(s['rotation'], dtype=np.float32),
        }
        for iid, s in data.items()
    }

def _to_json(item: dict) -> dict:
    return {
        'snap':     _snap_to_json(item['snap']),
        'regions':  _snap_to_json(item.get('regions', {})),
        'label':    item['label'],
        'duration': int(item.get('duration', 0)),
    }

def _from_json(d: dict) -> dict:
    return {
        'snap':     _snap_from_json(d['snap']),
        'regions':  _snap_from_json(d.get('regions', {})),
        'label':    d['label'],
        'duration': int(d.get('duration', 0)),
    }

class GlobalKeyframeStore:

    def __init__(self, window) -> None:
        self._window = window
        self._seq = KeyframeSequence(_to_json, _from_json)
        name = getattr(window, '_json_key', '') or 'default'
        self._path = json_root_path(name, _GLOBAL_JSON)
        self.animator = KeyframeAnimator(
            window, self._capture, self._apply, self._interpolate,
            ANNOT_ANIM_DURATION, ANNOT_ANIM_FPS, ANNOT_ANIM_EASING,
        )
        self.load()

    def seq(self) -> KeyframeSequence:
        return self._seq

    def clear(self) -> None:
        self._seq.clear()

    def display_path(self) -> str:
        from configs.settings import JSON_DIR
        return (f'{JSON_DIR.name}/{self._path.parent.name}/'
                f'{self._path.name}')

    def _controller(self):
        return getattr(self._window, '_input_transform', None)

    def _capture(self) -> dict | None:
        c = self._controller()
        if c is None:
            return None
        snap = {
            iid: {
                'center':   t.center.astype(np.float32).copy(),
                'size':     t.size.astype(np.float32).copy(),
                'rotation': t.rotation.astype(np.float32).copy(),
            }
            for iid, t in c.targets.items()
        }
        regions = global_region.capture(self._window)
        if not snap and not regions:
            return None
        return {'snap': snap, 'regions': regions}

    def _apply(self, state: dict) -> None:
        c = self._controller()
        if c is not None:
            for iid, s in state['snap'].items():
                t = c.targets.get(iid)
                if t is None:
                    continue
                t.center = s['center']
                t.size = s['size']
                t.rotation = s['rotation']
        global_region.apply(self._window, state.get('regions', {}))
        request_repaint(self._window)

    @staticmethod
    def _interpolate(src: dict, dst: dict, t: float) -> dict:
        return {
            'snap': global_region.lerp_transform_dict(
                src.get('snap', {}), dst.get('snap', {}), t),
            'regions': global_region.lerp_transform_dict(
                src.get('regions', {}), dst.get('regions', {}), t),
        }

    def save(self) -> None:
        write_keyframe_json(
            self._path, self._seq.to_list(), 'Global', logger)

    def load(self) -> None:
        data = read_keyframe_json(self._path, 'Global', logger)
        if data is None:
            return
        self._seq.from_list(data)
        logger.info('Global keyframes loaded: %s', self._path.name)

def _store(win):
    return getattr(win, '_global_keyframes', None)

def _has_objects(win) -> bool:
    c = getattr(win, '_input_transform', None)
    return bool(c is not None and c.targets)

def _overlay(win, message: str) -> None:
    win._message_overlay = message
    win._message_overlay_timer.start()

def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'

def handle_add_global_keyframe(win) -> None:
    store = _store(win)
    if store is None:
        return
    snap = store._capture()
    if snap is None or not _has_objects(win):
        logger.warning('No objects available for global keyframe')
        return
    seq = store.seq()
    first = seq.count() == 0
    default = f'Global Keyframe {seq.count() + 1}'
    label, duration, ok = prompt_keyframe(
        win, 'Add Global Keyframe', default,
        store.animator.duration_ms, first,
    )
    if not ok or not label:
        return
    before = seq.snapshot()
    seq.add({
        'snap':     snap['snap'],
        'regions':  snap.get('regions', {}),
        'label':    label,
        'duration': duration,
    })
    seq.set_cursor(seq.count() - 1)
    if ENABLE_INSTANT_JSON_SYNC:
        store.save()
    record_keyframe_seq(
        win, store, seq, before, seq.snapshot(), 'Add global keyframe',
    )
    _overlay(win, f'Global Keyframe Added: {keep_case(label)} [{seq.count()}]')
    request_repaint(win)

def handle_remove_global_keyframe(win) -> None:
    store = _store(win)
    if store is None:
        return
    seq = store.seq()
    before = seq.snapshot()
    removed_ord = seq.count()
    if seq.remove_last():
        if ENABLE_INSTANT_JSON_SYNC:
            store.save()
        record_keyframe_seq(
            win, store, seq, before, seq.snapshot(),
            'Remove global keyframe',
        )
        n = seq.count()
        if n == 0 and ENABLE_INSTANT_JSON_SYNC:
            msg = (f'Global {_ordinal(removed_ord)} Key Removed '
                   f'({store.display_path()} removed)')
        else:
            msg = (f'Global {_ordinal(removed_ord)} Key Removed. '
                   f'[{n}/{removed_ord}]')
        _overlay(win, msg)
        request_repaint(win)
    else:
        logger.warning('No global keyframes to remove')

def handle_clear_global_keyframes(win) -> None:
    store = _store(win)
    if store is None:
        return
    seq = store.seq()
    if seq.count() == 0:
        logger.warning('No global keyframes to clear')
        return
    store.animator.stop()
    before = seq.snapshot()
    seq.clear()
    if ENABLE_INSTANT_JSON_SYNC:
        store.save()
    record_keyframe_seq(
        win, store, seq, before, seq.snapshot(), 'Clear global keyframes',
    )
    suffix = (f' ({store.display_path()} removed)'
              if ENABLE_INSTANT_JSON_SYNC else '')
    _overlay(win, f'Global Keys Cleared{suffix}')
    request_repaint(win)

def _goto(win, delta: int) -> None:
    store = _store(win)
    if store is None:
        return
    seq = store.seq()
    item = seq.goto(delta)
    if item is None:
        logger.warning('No global keyframes to navigate')
        return
    store.animator.start(item)
    n = seq.count()
    _overlay(
        win,
        f'Global KEY [{seq.cursor() + 1}/{n}]: '
        f'{keep_case(item["label"])}',
    )

def handle_goto_next_global_keyframe(win) -> None:
    _goto(win, 1)

def handle_goto_prev_global_keyframe(win) -> None:
    _goto(win, -1)

def handle_toggle_global_keyframes(win) -> None:
    win._show_global_kf = not getattr(win, '_show_global_kf', True)
    state = 'On' if win._show_global_kf else 'Off'
    _overlay(win, f'Global Markers {state}.')
    logger.info('Global keyframe markers visible: %s', win._show_global_kf)
    request_repaint(win)

def compute_global_object_markers(
    win, viewmat, K, ortho: bool = False,
) -> list[tuple[int, int, str]]:
    if not getattr(win, '_show_global_kf', True):
        return []
    store = _store(win)
    if store is None:
        return []
    seq = store.seq()
    if seq.count() == 0:
        return []
    items = []
    for it in seq.items():
        base = it['label']
        for iid, s in it['snap'].items():
            items.append({
                'pos': s['center'],
                'label': f'{base} - {display_name(win, iid)}',
            })
        for rlabel, s in it.get('regions', {}).items():
            items.append({
                'pos': s['center'],
                'label': f'{base} - {rlabel}',
            })
    return compute_annotation_markers(items, viewmat, K, ortho=ortho)
