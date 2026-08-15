import logging

from process.common.widget import request_repaint
from process.undo import record_transform, snapshot_transform

logger = logging.getLogger(__name__)

def _resolve(window):

    controller = getattr(window, '_input_transform', None)
    if controller is None:
        return None, None
    sel = controller.selected_id
    if sel is None:
        ids = list(controller.targets.keys())
        sel = ids[0] if len(ids) == 1 else None
    return controller, sel

def reset_selected_object(window) -> bool:
    controller, sel = _resolve(window)
    if controller is None or sel is None:
        logger.warning('Reset object: no target selected')
        return False
    target = controller.targets.get(sel)
    if target is None:
        return False
    before = snapshot_transform(target)
    target.reset()
    after = snapshot_transform(target)
    record_transform(window, controller, sel, before, after)
    controller.point_scale.pop(sel, None)
    controller.bracket_mode.discard(sel)
    on_change = getattr(controller, 'on_change', None)
    if callable(on_change):
        on_change()
    request_repaint(window)
    logger.info('Reset object: %s', sel)
    return True
