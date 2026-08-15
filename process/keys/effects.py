import logging

import numpy as np

logger = logging.getLogger(__name__)

def handle_cycle_world_rot(win) -> None:
    from process.camera import cycle_world_rot
    old_mat, new_mat, _ = cycle_world_rot()
    ply_c = old_mat.T @ win._cam['target'].astype(np.float32)
    win._cam['target'] = (new_mat @ ply_c).astype(np.float64)
    win._cam_dirty = True
    win._update_cam()

def handle_toggle_mesh(win) -> None:
    new_state = not win._show_bbox
    win._show_bbox = new_state
    win._show_grid = new_state
    win._depth_occlusion = new_state
    win._render_current()
    logger.info('Mesh overlay: %s', new_state)

def handle_toggle_depth_occlusion(win) -> None:
    win._depth_occlusion = not win._depth_occlusion
    win._render_current()
    logger.info('Depth occlusion: %s', win._depth_occlusion)

def handle_toggle_corner_bracket(win) -> None:
    itc = getattr(win, '_input_transform', None)
    sel_obj = getattr(itc, 'selected_id', None) if itc is not None else None
    if sel_obj is not None and itc is not None:
        itc.toggle_bracket_mode(sel_obj)
        win._render_current()
        logger.info('Corner bracket mode toggled (object %s)', sel_obj)
        return
    region_toggle = getattr(win, '_corner_bracket_region_toggle', None)
    if callable(region_toggle) and region_toggle():
        win._render_current()
        logger.info('Corner bracket mode toggled (region)')
        return
    logger.info('Corner bracket mode: no selection to toggle')

def handle_toggle_logs(win) -> None:
    win._show_logs = not win._show_logs
    if not win._show_logs:
        win._widget.set_log_overlay([])
    win._render_current()
    logger.info('Log overlay: %s', win._show_logs)

def handle_toggle_fog(win) -> None:
    win._fog_enabled = not win._fog_enabled
    win._render_current()
    logger.info('Fog effect: %s', win._fog_enabled)

def handle_toggle_turntable(win) -> None:
    win._turntable = not win._turntable
    logger.info('Turntable: %s', win._turntable)

def handle_toggle_sequence_overlay(win) -> None:
    widget = win._widget
    new_state = not widget._sequence_overlay_visible
    widget._sequence_overlay_visible = new_state
    widget.update()
    logger.info('Sequence overlay: %s', new_state)

def apply_all_overlays_visible(win, visible: bool) -> None:
    widget = win._widget
    widget.set_overlays_visible(visible)
    widget._attr_overlay_hidden = not visible
    for hook in getattr(win, '_overlay_visibility_hooks', ()):
        try:
            hook(visible)
        except Exception:
            logger.exception('Overlay visibility hook error')
    widget.update()

def handle_toggle_all_overlays(win) -> None:
    visible = not win._widget._overlays_visible
    apply_all_overlays_visible(win, visible)
    logger.info('All overlays: %s', visible)

def handle_toggle_attr_overlay(win) -> None:
    widget = win._widget
    hidden = not getattr(widget, '_attr_overlay_hidden', False)
    widget._attr_overlay_hidden = hidden
    widget.update()
    logger.info('Attribute overlay hidden: %s', hidden)

def handle_toggle_preview_overlays(win) -> None:
    widget = win._widget
    apply_compact_overlays(
        win, not getattr(widget, '_compact_overlays', False),
    )

def apply_compact_overlays(win, state: bool) -> None:
    win._widget._compact_overlays = state
    for hook in getattr(win, '_preview_hooks', ()):
        try:
            hook(state)
        except Exception:
            logger.exception('Preview hook error')
    win._render_current()
    logger.info('Compact overlays (preview): %s', state)

def handle_record_toggle(win) -> None:
    win._toggle_live_recording()

def handle_toggle_help(win) -> None:
    win._show_help = not win._show_help
    if win._show_help and win._show_plugin_help:
        win._show_plugin_help = False
        win._widget.set_plugin_help_visible(False)

    win._help_page = 0
    win._widget.set_help_page(0)
    win._widget.set_help_visible(win._show_help)
    win._widget.update()
    logger.info('Help overlay: %s', win._show_help)

def handle_toggle_plugin_help(win) -> None:
    win._show_plugin_help = not win._show_plugin_help
    if win._show_plugin_help and win._show_help:
        win._show_help = False
        win._widget.set_help_visible(False)

    win._plugin_help_page = 0
    win._widget.set_plugin_help_sections(win._plugin_help_sections)
    win._widget.set_plugin_help_page(0)
    win._widget.set_plugin_help_visible(win._show_plugin_help)
    win._widget.update()
    logger.info('Plugin help overlay: %s', win._show_plugin_help)
