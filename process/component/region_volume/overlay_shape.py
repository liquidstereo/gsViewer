from typing import Any, Callable

import numpy as np
from PySide6.QtGui import QPainter

from process.component.region_volume.hover_select import region_is_selected
from process.component.region_volume.overlay import (
    RegionPalette, paint_region, paint_region_hull, resolve_palette,
)

def paint_shape_region(
    painter: QPainter, win: Any, region: Any,
    w: int, h: int, depth: np.ndarray | None,
    segments: list,
    palette: RegionPalette | None = None,
    selected: bool = False,
) -> None:
    paint_region_hull(painter, segments, palette, selected)
    paint_region(
        painter, segments, depth, w, h,
        win=win, region=region, bold=selected, palette=palette,
    )

def make_shape_painter(
    plugin: Any, window: Any,
    paint_fn: Callable[..., None],
    palette: RegionPalette | None = None,
) -> Callable[[QPainter, int, int, np.ndarray | None], None]:
    def _paint(
        painter: QPainter, w: int, h: int,
        depth: np.ndarray | None,
    ) -> None:
        if not plugin.region_visible:
            return
        locked = getattr(plugin, 'region_locked', False)
        selected = region_is_selected(plugin)
        pal = resolve_palette(palette, locked, selected)
        paint_fn(painter, window, plugin.region, w, h, depth, pal, selected)

    return _paint
