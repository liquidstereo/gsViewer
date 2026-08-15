import logging

from process.keys.camera import handle_reset_camera

logger = logging.getLogger(__name__)

def _reset_input_transforms(win) -> None:
    controller = getattr(win, '_input_transform', None)
    if controller is None:
        return
    for target in controller.targets.values():
        target.reset()
    controller.locked.clear()
    controller.selected_id = None
    controller.on_change()

def handle_home_reset(win) -> None:

    from process.reset.region import reset_region_volume_plugins
    _reset_input_transforms(win)
    reset_region_volume_plugins(win)
    handle_reset_camera(win)
    render = getattr(win, '_render_current', None)
    if render is not None:
        render()
    logger.info('Full reset to initial state')
