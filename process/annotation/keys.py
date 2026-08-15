import logging

from configs.settings import ENABLE_INSTANT_JSON_SYNC
from process.annotation.dialog import prompt_camera_keyframe
from process.camera import cam_pos_from_viewmat
from process.widget.text_case import keep_case

logger = logging.getLogger(__name__)

def _dismiss_message_overlay(win) -> None:
    win._message_overlay = ''
    win._message_overlay_timer.stop()

def handle_add_annotation(win) -> None:
    first = win._annot.count() == 0
    default = f'Camera Keyframe {win._annot.count() + 1}'
    label, duration, ok = prompt_camera_keyframe(
        win, default, win._annot_animator.duration_ms, first,
    )
    if not ok or not label:
        return
    eye_pos = cam_pos_from_viewmat(win._viewmat).cpu().numpy()
    win._annot.add(win._cam, eye_pos, label, duration)
    win._annot_cursor = win._annot.count() - 1
    if ENABLE_INSTANT_JSON_SYNC:
        win._annot.save(win._annot_file)
    _dismiss_message_overlay(win)
    win._render_current()
    logger.info('Annotation %r added (duration=%d ms)', label, duration)

def handle_remove_annotation(win) -> None:
    if win._annot.remove_last():
        win._annot.save(win._annot_file)
        _dismiss_message_overlay(win)
        win._render_current()
    else:
        logger.warning('No annotations to remove')

def handle_toggle_annotations(win) -> None:
    win._show_annot = not win._show_annot
    _dismiss_message_overlay(win)
    win._render_current()
    logger.info('Annotations visible: %s', win._show_annot)

def _goto_annotation(win, delta: int) -> None:
    if win._annot.count() == 0:
        return
    n = win._annot.count()
    if win._annot_cursor == -1:
        win._annot_cursor = 0 if delta > 0 else n - 1
    else:
        win._annot_cursor = (win._annot_cursor + delta) % n
    item = win._annot.items()[win._annot_cursor]
    win._message_overlay = keep_case(item['label'])
    win._message_overlay_timer.start()
    win._annot_animator.start(item)
    logger.info(
        'Goto annotation [%d/%d]: %r',
        win._annot_cursor + 1, n, item['label'],
    )

def handle_goto_next_annotation(win) -> None:
    _goto_annotation(win, 1)

def handle_goto_prev_annotation(win) -> None:
    _goto_annotation(win, -1)

def handle_clear_all(win) -> None:
    win._annot.clear()
    win._annot.save(win._annot_file)
    win._annot_cursor = -1
    win._message_overlay = 'All Camera Keyframes cleared'
    win._message_overlay_timer.start()
    win._render_current()
    logger.info('All annotations cleared')
