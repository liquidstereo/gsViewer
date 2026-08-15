import logging
from configs.settings_effects import (
    SPLAT_SCALE_DEFAULT, SPLAT_SCALE_FACTOR,
    SPLAT_SCALE_MIN, SPLAT_SCALE_MAX,
)
from process.common.widget import set_message_overlay
from process.data.pointcloud_buffer import is_pointcloud_splat
from process.mode import RenderMode, MODE_NAMES, startup_mode
from process.undo import record_object_state, snapshot_object_state

logger = logging.getLogger(__name__)

GAUSSIAN_ONLY_MESSAGE: str = 'Point cloud input: only Point Cloud (GL)'
POINTCLOUD_ONLY_MESSAGE: str = 'Gaussian input: Point Cloud (GL) needs a '\
    'pure .ply point cloud'

def _blocked_reason(win, target: RenderMode) -> str:

    is_cloud = is_pointcloud_splat(getattr(win, '_splat', None))
    if is_cloud and target != RenderMode.GL_POINTS:
        return GAUSSIAN_ONLY_MESSAGE
    if not is_cloud and target == RenderMode.GL_POINTS:
        return POINTCLOUD_ONLY_MESSAGE
    return ''

def _set_mode(win, mode: RenderMode) -> None:
    target = startup_mode() if win._render_mode == mode else mode
    reason = _blocked_reason(win, target)
    if reason:
        set_message_overlay(win, reason)
        logger.info('Render mode change cancelled: %s', reason)
        return
    name = MODE_NAMES[int(target)]
    win._render_mode = target
    win._message_overlay = name

    win._hover_overlay = ''
    win._message_overlay_timer.start()
    win._render_current()
    logger.info('Render mode: %s', name)

def handle_mode_default(win) -> None:
    _set_mode(win, RenderMode.DEFAULT)

def handle_mode_normal(win) -> None:
    _set_mode(win, RenderMode.NORMAL)

def handle_mode_point(win) -> None:
    _set_mode(win, RenderMode.POINT)

def handle_mode_aniso(win) -> None:
    _set_mode(win, RenderMode.ANISO)

def handle_mode_opacity(win) -> None:
    _set_mode(win, RenderMode.OPACITY)

def handle_mode_accumulation(win) -> None:
    _set_mode(win, RenderMode.ACCUMULATION)

def handle_mode_scale(win) -> None:
    _set_mode(win, RenderMode.SCALE)

def handle_mode_sh(win) -> None:
    _set_mode(win, RenderMode.SH)

def handle_mode_gl_points(win) -> None:
    _set_mode(win, RenderMode.GL_POINTS)

def handle_mode_rotation(win) -> None:
    _set_mode(win, RenderMode.ROTATION)

def handle_mode_hit_count(win) -> None:
    _set_mode(win, RenderMode.HIT_COUNT)

def handle_mode_median_depth(win) -> None:
    _set_mode(win, RenderMode.MEDIAN_DEPTH)

def _adjust_splat_size(win, factor: float) -> None:
    mult = win._scale_mult * factor
    mult = max(SPLAT_SCALE_MIN, min(SPLAT_SCALE_MAX, mult))
    win._scale_mult = mult

    win._render_current()
    logger.info('Splat size mult: %.3f', mult)

def handle_splat_size_up(win) -> None:
    _adjust_splat_size(win, SPLAT_SCALE_FACTOR)

def handle_splat_size_down(win) -> None:
    _adjust_splat_size(win, 1.0 / SPLAT_SCALE_FACTOR)

def _reset_point_scales(win) -> None:
    controller = getattr(win, '_input_transform', None)
    point_scale = getattr(controller, 'point_scale', None)
    if point_scale is not None:
        point_scale.clear()

def handle_splat_size_reset(win) -> None:
    ctrl = getattr(win, '_input_transform', None)
    before = snapshot_object_state(win, ctrl) if ctrl is not None else None
    win._scale_mult = SPLAT_SCALE_DEFAULT
    _reset_point_scales(win)

    win._render_current()
    if ctrl is not None and before is not None:
        record_object_state(
            win, ctrl, before, snapshot_object_state(win, ctrl),
            'Splat size reset',
        )
    logger.info('Splat size mult reset: %.3f', SPLAT_SCALE_DEFAULT)
