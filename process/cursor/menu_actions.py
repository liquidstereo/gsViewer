import logging

from process.console.attr_buttons import reset_plugin_defaults

logger = logging.getLogger(__name__)

def has_reset(plugin) -> bool:
    if callable(getattr(plugin, 'reset_to_default', None)):
        return True
    system = getattr(plugin, 'system', None)
    return system is not None and callable(getattr(system, 'reset', None))

def apply_reset(window, plugin) -> bool:
    full = getattr(plugin, 'reset_to_default', None)
    if callable(full):
        full(window)
        logger.info('Context menu reset: %s (full defaults)',
                    getattr(plugin, 'overlay_label', '?'))
        return True
    system = getattr(plugin, 'system', None)
    if system is None or not callable(getattr(system, 'reset', None)):
        return False
    reset_plugin_defaults(plugin)
    logger.info('Context menu reset: %s (parameter defaults)',
                getattr(plugin, 'overlay_label', '?'))
    return True
