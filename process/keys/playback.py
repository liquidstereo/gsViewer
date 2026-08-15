import logging

from process.transform.attr_overlay import close_attr_editor_panel
from process.widget.paint_help import HELP_PAGE_COUNT

logger = logging.getLogger(__name__)

def _show_message_overlay(win, text: str) -> None:
    if not hasattr(win, '_message_overlay'):
        return
    win._message_overlay = text
    timer = getattr(win, '_message_overlay_timer', None)
    if timer is not None:
        timer.start()

def _run_pause_hooks(win, paused: bool) -> None:
    hooks = getattr(win, '_pause_hooks', None)
    if not hooks:
        return
    for hook in hooks:
        try:
            hook(paused)
        except Exception:
            logger.exception('Pause hook error')

def _run_seek_sync(win) -> None:

    hook = getattr(win, '_playback_seek_sync', None)
    if hook is None:
        return
    try:
        hook()
    except Exception:
        logger.exception('Seek sync hook error')

def handle_play_pause(win) -> None:
    win._playing = not win._playing
    if win._playing:

        if getattr(win, '_needs_rebuffer', False):
            win._needs_rebuffer = False
            win._run_buffer_stages()
        win._reset_playback_clock()
        win._timer.start()

        win._run_playback_start_hooks()
        _show_message_overlay(win, 'PLAY')
        logger.info('Playback started')
    else:
        win._timer.stop()
        _show_message_overlay(win, 'PAUSE')
        logger.info('Playback paused')
    win._render_current()
    _run_pause_hooks(win, paused=not win._playing)

def _help_overlay_active(win) -> bool:
    return bool(
        getattr(win, '_show_help', False)
        or getattr(win, '_show_plugin_help', False)
    )

def _page_main_help(win, delta: int) -> None:
    if HELP_PAGE_COUNT <= 1:
        return
    page = (getattr(win, '_help_page', 0) + delta) % HELP_PAGE_COUNT
    win._help_page = page
    win._widget.set_help_page(page)
    win._widget.update()
    logger.debug('Main help page -> %d/%d', page + 1, HELP_PAGE_COUNT)

def _page_plugin_help(win, delta: int) -> None:
    if not getattr(win, '_show_plugin_help', False):
        return
    sections = getattr(win, '_plugin_help_sections', [])
    n = len(sections)
    if n <= 1:
        return
    page = (getattr(win, '_plugin_help_page', 0) + delta) % n
    win._plugin_help_page = page
    win._widget.set_plugin_help_page(page)
    win._widget.update()
    logger.debug('Plugin help page -> %d/%d', page + 1, n)

def _page_active_help(win, delta: int) -> None:
    if getattr(win, '_show_help', False):
        _page_main_help(win, delta)
        return
    _page_plugin_help(win, delta)

def handle_prev_frame(win) -> None:

    if _help_overlay_active(win):
        _page_active_help(win, -1)
        return
    win._timer.stop()
    win._playing = False
    win.set_frame(win._idx - 1)
    _run_seek_sync(win)

def handle_next_frame(win) -> None:
    if _help_overlay_active(win):
        _page_active_help(win, +1)
        return
    win._timer.stop()
    win._playing = False
    win.set_frame(win._idx + 1)
    _run_seek_sync(win)

def handle_first_frame(win) -> None:
    if _help_overlay_active(win) or win._total_frames <= 1:
        return
    win._timer.stop()
    win._playing = False

    hook = getattr(win, '_timeline_seek', None)
    if hook is not None and hook(0.0):
        _run_seek_sync(win)
        return
    win.set_frame(0)
    _run_seek_sync(win)

def handle_last_frame(win) -> None:
    if _help_overlay_active(win) or win._total_frames <= 1:
        return
    win._timer.stop()
    win._playing = False

    hook = getattr(win, '_timeline_seek', None)
    if hook is not None and hook(1.0):
        _run_seek_sync(win)
        return
    win.set_frame(win._total_frames - 1)
    _run_seek_sync(win)

def _close_help_overlays(win) -> bool:
    closed = False
    if getattr(win, '_show_help', False):
        win._show_help = False
        win._widget.set_help_visible(False)
        closed = True
    if getattr(win, '_show_plugin_help', False):
        win._show_plugin_help = False
        win._widget.set_plugin_help_visible(False)
        closed = True
    if closed:
        win._widget.update()
    return closed

def _close_attr_editor(win) -> bool:
    return close_attr_editor_panel(win)

def handle_quit(win) -> None:
    if _close_help_overlays(win):
        logger.info('Help overlay closed by Esc')
        return
    if _close_attr_editor(win):
        logger.info('Attribute editor closed by Esc')
        return
    if not win._confirm_close():
        return
    win._force_exit()
