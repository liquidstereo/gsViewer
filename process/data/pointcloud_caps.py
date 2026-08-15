import importlib
import logging

from process.common.widget import set_message_overlay
from process.data.pointcloud_buffer import is_pointcloud_splat

logger = logging.getLogger(__name__)

CAPABILITY_FLAG: str = 'POINTCLOUD_SUPPORTED'
PLUGIN_ROOT: str = 'plugins'
NOTICE_FLAG: str = '_pointcloud_notice_shown'
UNSUPPORTED_MESSAGE: str = 'Plugins not supported on point cloud input'

def _package_of(module: str) -> str | None:
    parts = (module or '').split('.')
    if len(parts) >= 2 and parts[0] == PLUGIN_ROOT:
        return parts[1]
    return None

def _closure_owner(proc) -> str | None:

    for cell in getattr(proc, '__closure__', None) or ():
        try:
            value = cell.cell_contents
        except ValueError:
            continue
        name = _package_of(type(value).__module__)
        if name is not None:
            return name
    return None

def plugin_package(proc) -> str | None:
    owner = getattr(proc, '_gate_plugin', None)
    if owner is None:
        owner = getattr(proc, '__self__', None)
    if owner is not None:
        return _package_of(type(owner).__module__)
    return (_closure_owner(proc)
            or _package_of(getattr(proc, '__module__', '')))

def supports_point_cloud(name: str | None) -> bool:
    if not name:
        return False
    try:
        settings = importlib.import_module(
            f'{PLUGIN_ROOT}.{name}.settings')
    except ModuleNotFoundError:
        logger.debug('No settings module for plugin %s', name)
        return False
    return bool(getattr(settings, CAPABILITY_FLAG, False))

def partition_processors(procs) -> tuple[list, list]:
    runnable = []
    blocked = set()
    for proc in procs or []:
        name = plugin_package(proc)
        if supports_point_cloud(name):
            runnable.append(proc)
            continue
        if name:
            blocked.add(name)
    return runnable, sorted(blocked)

def cloud_processors(window) -> tuple[list, list]:
    procs = tuple(getattr(window, '_frame_processors', ()) or ())
    cached = getattr(window, '_pointcloud_proc_cache', None)
    if cached is not None and cached[0] == procs:
        return cached[1], cached[2]
    runnable, blocked = partition_processors(procs)
    window._pointcloud_proc_cache = (procs, runnable, blocked)
    if blocked:
        logger.info('Plugins skipped on point cloud input: %s',
                    ', '.join(blocked))
    return runnable, blocked

def _is_cloud_window(win) -> bool:
    return is_pointcloud_splat(getattr(win, '_splat', None))

def notify_unsupported(win) -> bool:
    if getattr(win, NOTICE_FLAG, False) or not _is_cloud_window(win):
        return False
    blocked = cloud_processors(win)[1]
    if not blocked:
        return False
    setattr(win, NOTICE_FLAG, True)
    set_message_overlay(win, f'{UNSUPPORTED_MESSAGE}: {", ".join(blocked)}')
    return True

def notify_if_unsupported(win, handler) -> bool:
    if not _is_cloud_window(win):
        return False
    name = plugin_package(handler)
    if not name or supports_point_cloud(name):
        return False
    set_message_overlay(win, f'{UNSUPPORTED_MESSAGE}: {name}')
    logger.info('Plugin %s has no effect on point cloud input', name)
    return True
