import logging

logger = logging.getLogger(__name__)

def handle_toggle_colormap(win) -> None:
    win._show_colormap = not win._show_colormap
    win._render_current()
    logger.info('Colormap overlay: %s', win._show_colormap)
