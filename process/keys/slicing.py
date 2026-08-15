import logging

from PySide6.QtCore import QTimer

from configs.settings import (
    SLICE_RATIO_APPLY_DELAY_MS,
    SLICE_RATIO_MIN,
    SLICE_RATIO_STEP,
)
from process.data.loader import configure_slicing, get_slice_ratio

logger = logging.getLogger(__name__)

def _baseline_ratio(win) -> float:
    val = getattr(win, '_baseline_slice_ratio', None)
    if val is None:
        val = get_slice_ratio()
        win._baseline_slice_ratio = val
    return val

def _pending_ratio(win) -> float:
    val = getattr(win, '_pending_slice_ratio', None)
    return val if val is not None else get_slice_ratio()

def _schedule_apply(win) -> None:
    timer = getattr(win, '_slice_apply_timer', None)
    if timer is None:
        timer = QTimer(win)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: _commit_ratio(win))
        win._slice_apply_timer = timer
    timer.start(SLICE_RATIO_APPLY_DELAY_MS)

def _commit_ratio(win) -> None:
    new = getattr(win, '_pending_slice_ratio', None)
    win._pending_slice_ratio = None
    if new is None:
        return
    cur = get_slice_ratio()
    if new == cur:
        return
    configure_slicing(new < 1.0, new)
    for entry in win._inputs.values():
        entry['buf'].invalidate_slice()
    win.set_frame(win._idx)
    win._rebuffer_after_reload()

    logger.info(
        'Slice ratio committed: %.3f -> %.3f', cur, new,
        extra={'overlay': False},
    )

def _stage_ratio(win, new: float) -> bool:
    new = max(SLICE_RATIO_MIN, min(1.0, round(new, 3)))
    if new == _pending_ratio(win):
        return False
    win._pending_slice_ratio = new
    win._message_overlay = f'Ratio: {new:.2f}'
    win._message_overlay_timer.start()
    return True

def _set_target_ratio(win, new: float) -> None:
    if _stage_ratio(win, new):
        _schedule_apply(win)

def ui_get_ratio(win) -> float:
    return _pending_ratio(win)

def ui_stage_ratio(win, value: float) -> None:
    _baseline_ratio(win)
    _stage_ratio(win, float(value))

def ui_commit_ratio(win) -> None:
    _commit_ratio(win)

def handle_slice_ratio_up(win) -> None:
    _baseline_ratio(win)
    _set_target_ratio(win, _pending_ratio(win) + SLICE_RATIO_STEP)

def handle_slice_ratio_down(win) -> None:
    _baseline_ratio(win)
    _set_target_ratio(win, _pending_ratio(win) - SLICE_RATIO_STEP)

def handle_slice_ratio_reset(win) -> None:
    _set_target_ratio(win, _baseline_ratio(win))
