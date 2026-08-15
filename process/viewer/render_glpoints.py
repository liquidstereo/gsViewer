import logging

import numpy as np

from configs.settings_camera import NEAR_PLANE
from configs.settings_color import BACKGROUND_COLOR
from configs.settings_glpoints import GLPOINTS_POINT_SIZE
from process.common import hex_to_rgb
from process.common.widget import set_message_overlay
from process.renderer.core import get_far_plane
from process.renderer.glpoints import GLPointRenderer

logger = logging.getLogger(__name__)

GL_UNAVAILABLE_MESSAGE: str = 'GL point renderer unavailable'

def get_gl_point_renderer(win) -> GLPointRenderer:
    renderer = getattr(win, '_gl_point_renderer', None)
    if renderer is None:
        renderer = GLPointRenderer()
        win._gl_point_renderer = renderer
    return renderer

def _background_frame(w: int, h: int) -> np.ndarray:
    rgb = np.round(
        np.array(hex_to_rgb(BACKGROUND_COLOR), dtype=np.float32) * 255.0
    ).astype(np.uint8)
    return np.ascontiguousarray(np.tile(rgb, (h, w, 1)))

def render_gl_points_frame(win, splat: dict) -> np.ndarray:
    renderer = get_gl_point_renderer(win)
    arr = renderer.render(
        splat.get('means_np'), splat.get('colors_np'),
        win._viewmat, win._K, win._w, win._h,
        NEAR_PLANE, get_far_plane(),
        camera_model=win._camera_model,
        point_size=GLPOINTS_POINT_SIZE * win._scale_mult,
        opacities=splat.get('opacities'),
    )
    if arr is not None:
        return arr
    if not getattr(win, '_gl_point_warned', False):
        win._gl_point_warned = True
        set_message_overlay(win, GL_UNAVAILABLE_MESSAGE)
        logger.error('GL point render failed - showing background only')
    return _background_frame(win._w, win._h)
