import logging

from process.common.widget import request_repaint
from process.handle import set_message_overlay

logger = logging.getLogger(__name__)

PAUSE_TO_SELECT_MSG = 'Pause playback to select.'

def is_single_active_mode(win) -> bool:
    if getattr(win, '_chain_segments', None):
        return True
    return getattr(win, '_scheduler', None) is not None

def active_input_id(win) -> str | None:
    if getattr(win, '_chain_segments', None):
        return getattr(win, '_chain_active_iid', None)
    sch = getattr(win, '_scheduler', None)
    if sch is not None:
        ids = list(getattr(win, '_inputs', {}))
        idx = sch.active()
        if 0 <= idx < len(ids):
            return ids[idx]
    return None

def selection_allowed(win, input_id: str) -> bool:
    if not is_single_active_mode(win):
        return True
    if not getattr(win, '_playing', False):
        return True
    return input_id == active_input_id(win)

def notify_pause_required(win) -> None:
    set_message_overlay(win, PAUSE_TO_SELECT_MSG)
    request_repaint(win)

def seek_to_input(win, input_id: str) -> None:

    win._needs_rebuffer = True
    segs = getattr(win, '_chain_segments', None)
    if segs:
        for iid, start, _length in segs:
            if iid == input_id:
                win.set_frame(start)
                return
        return
    sch = getattr(win, '_scheduler', None)
    if sch is None:
        return
    ids = list(getattr(win, '_inputs', {}))
    if input_id in ids:
        sch.jump_to(ids.index(input_id))
        win._render_playlist_frame()
