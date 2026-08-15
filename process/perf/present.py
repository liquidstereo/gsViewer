import logging
import os
import time

from configs.settings import PLAYBACK_FPS
from process.scroll.overlay_scroll import CHILD_PAINT

logger = logging.getLogger(__name__)

PRESENT_PERF: bool = os.environ.get('GSVIEWER_PRESENT_PERF') == '1'

_WINDOW = 60

def note_render(win, ms: float) -> None:
    win._pp_render_ms = getattr(win, '_pp_render_ms', 0.0) + ms
    win._pp_render_n = getattr(win, '_pp_render_n', 0) + 1
    if ms > getattr(win, '_pp_render_max', 0.0):
        win._pp_render_max = ms

def note_save(win, ms: float) -> None:
    win._pp_save_ms = getattr(win, '_pp_save_ms', 0.0) + ms
    win._pp_save_n = getattr(win, '_pp_save_n', 0) + 1

def note_clamp(win, elapsed: float, max_catchup: int) -> None:
    if PLAYBACK_FPS <= 0:
        return
    win._pp_clamp = getattr(win, '_pp_clamp', 0) + 1
    win._pp_lost = getattr(win, '_pp_lost', 0.0) + (
        elapsed - max_catchup / PLAYBACK_FPS) * 1000.0

def present_tick(win, now: float) -> None:
    win._pp_n = getattr(win, '_pp_n', 0) + 1
    last = getattr(win, '_pp_last', 0.0)
    if last > 0.0:
        loop_ms = (now - last) * 1000.0
        win._pp_loop = getattr(win, '_pp_loop', 0.0) + loop_ms
        if loop_ms > getattr(win, '_pp_loop_max', 0.0):
            win._pp_loop_max = loop_ms
    win._pp_last = now

    paint_end = getattr(win._widget, '_pp_paint_end', 0.0)
    if paint_end > 0.0:
        win._pp_post = getattr(win, '_pp_post', 0.0) + (
            now - paint_end) * 1000.0
        win._pp_post_n = getattr(win, '_pp_post_n', 0) + 1
    if win._pp_n < _WINDOW:
        return

    if not getattr(win, '_pp_warmed', False):
        win._pp_warmed = True

        win._pp_tick0 = win._anim_tick
        _reset(win, win._widget)
        return
    _log_window(win)

def _log_window(win) -> None:

    w = win._widget
    n = win._pp_n
    loop = getattr(win, '_pp_loop', 0.0) / n
    render_n = getattr(win, '_pp_render_n', 0)
    render = (getattr(win, '_pp_render_ms', 0.0) / render_n
              if render_n else 0.0)
    paint_n = getattr(w, '_pp_paint_n', 0)
    paint = (getattr(w, '_pp_paint_ms', 0.0) / paint_n) if paint_n else 0.0
    child_n, child_ms = CHILD_PAINT[0], CHILD_PAINT[1]
    child = (child_ms / child_n) if child_n else 0.0
    post_n = getattr(win, '_pp_post_n', 0)
    post = (getattr(win, '_pp_post', 0.0) / post_n) if post_n else 0.0
    save_n = getattr(win, '_pp_save_n', 0)
    save = (getattr(win, '_pp_save_ms', 0.0) / save_n) if save_n else 0.0

    span = getattr(win, '_pp_loop', 0.0) / 1000.0
    d_tick = win._anim_tick - getattr(win, '_pp_tick0', win._anim_tick)
    win._pp_tick0 = win._anim_tick
    anim_hz = (d_tick / span) if span > 0 else 0.0
    logger.info(
        'PRESENT_PERF loop=%.1fms (%.1f Hz) render=%.1fms x%.2f '
        'paint=%.1fms x%.2f child=%.1fms x%.2f save=%.1fms x%.2f '
        'post=%.1fms gap=%.1fms '
        'anim_hz=%.1f (%.0f%% realtime) clamp=%d lost=%.0fms '
        'loop_max=%.0fms render_max=%.0fms anim_tick=%d',
        loop, (1000.0 / loop) if loop > 0 else 0.0,
        render, render_n / n, paint, paint_n / n, child, child_n / n,
        save, save_n / n, post,
        loop - render * (render_n / n) - paint * (paint_n / n)
        - save * (save_n / n),
        anim_hz, (anim_hz / PLAYBACK_FPS * 100.0) if PLAYBACK_FPS else 0.0,
        getattr(win, '_pp_clamp', 0), getattr(win, '_pp_lost', 0.0),
        getattr(win, '_pp_loop_max', 0.0),
        getattr(win, '_pp_render_max', 0.0), win._anim_tick,
    )
    _reset(win, w)

def _reset(win, widget) -> None:
    win._pp_n = 0
    win._pp_loop = 0.0
    win._pp_render_ms = 0.0
    win._pp_render_n = 0
    win._pp_post = 0.0
    win._pp_post_n = 0
    win._pp_save_ms = 0.0
    win._pp_save_n = 0
    win._pp_clamp = 0
    win._pp_lost = 0.0
    win._pp_loop_max = 0.0
    win._pp_render_max = 0.0
    widget._pp_paint_n = 0
    widget._pp_paint_ms = 0.0
    CHILD_PAINT[0] = 0
    CHILD_PAINT[1] = 0.0

def now_ms() -> float:
    return time.perf_counter()
