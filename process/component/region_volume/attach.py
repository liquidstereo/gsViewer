import logging
from typing import Callable

from process.component.region_volume.manager import register_box_controller
from process.component.region_volume.overlay import RegionPalette
from process.component.region_volume.registry import get_registry, renumber_box_labels

def _guarded_processor(window, plugin):
    def _proc(splat: dict) -> dict:
        if plugin not in get_registry(window).members:
            return splat
        return plugin._process_frame(splat)

    _proc._gate_plugin = plugin
    return _proc

def attach_box_plugin(
    window,
    plugin,
    channel: str,
    shape: str,
    register_attributes: Callable,
    log_name: str,
    region_palette: RegionPalette | None = None,
    region_painter_override: Callable | None = None,
    with_keyframes: bool = True,
) -> None:
    setattr(window, channel, plugin)

    plugin._channel = channel

    base = type(plugin).overlay_label
    reg = get_registry(window)
    same = sum(1 for m in reg.members
               if getattr(m, '_base_label', None) == base)
    plugin._base_label = base
    if same > 0:
        plugin.overlay_label = f'{base} {same + 1}'
    palette = region_palette if region_palette is not None else RegionPalette()
    register_box_controller(
        window, plugin,
        region_palette=palette,
        with_keyframes=with_keyframes,
        region_painter_override=region_painter_override,
        shape=shape,
    )
    renumber_box_labels(window, base)
    window._frame_processors.append(_guarded_processor(window, plugin))
    plugin._register_keys(window)
    register_attributes(window, plugin)
    plugin._register_help(window)
    logging.getLogger(type(plugin).__module__).info(
        '%s plugin attached', log_name)
