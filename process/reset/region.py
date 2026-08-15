import logging

logger = logging.getLogger(__name__)

def _restore_default_shape(plugin) -> None:
    default = getattr(plugin, '_default_shape', None)
    if not default or getattr(plugin, 'shape', None) == default:
        return
    rebuild = getattr(plugin, 'rebuild_region', None)
    if not callable(rebuild):
        return
    rebuild(default)
    win = getattr(plugin, '_window', None)
    autosize = getattr(plugin, '_autosize_region', None)
    if win is not None and callable(autosize):
        autosize(win)

def _reset_single_region_plugin(plugin) -> None:
    animator = getattr(plugin, 'keyframe_animator', None)
    if animator is not None:
        animator.stop()
    _restore_default_shape(plugin)
    region = getattr(plugin, 'region', None)
    if region is not None:
        region.reset()
    region_path = getattr(plugin, 'region_path', None)
    if region is not None and region_path is not None:
        try:
            region.delete_file(region_path)
        except Exception:
            logger.exception('Region file delete failed: %s', region_path)
    delete_curves = getattr(plugin, 'delete_curves', None)
    if callable(delete_curves):
        delete_curves()
    on_reset = getattr(plugin, 'on_reset', None)
    if callable(on_reset):
        on_reset()

def reset_region_volume_plugins(win) -> None:
    reg = getattr(win, '_region_volume_registry', None)

    if reg is not None:
        reg.solo_index = -1
        reg._solo_saved_vis = {}
    for plugin in list(getattr(reg, 'members', []) or []):
        _reset_single_region_plugin(plugin)
