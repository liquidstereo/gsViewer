import logging

import numpy as np
from PySide6.QtGui import QColor, QPainter

from process.common.font import make_font
from configs.settings_style import DESELECTED_COLOR
from process.common import hex_to_rgb
from process.component.region_volume.picking import project_point
from process.component.region_volume.settings import (
    REGION_VOLUME_LABEL_OUTLINE_ALPHA, REGION_VOLUME_LABEL_OUTLINE_COLOR,
    REGION_VOLUME_LABEL_PIXEL_SIZE, REGION_VOLUME_LABEL_TEXT_ALPHA_F,
    REGION_VOLUME_LABEL_Y_OFFSET,
)

logger = logging.getLogger(__name__)

def paint_region_label(
    painter: QPainter, win, region, text: str,
    color: str | None = None, bold: bool = False,
    pixel_size: int = REGION_VOLUME_LABEL_PIXEL_SIZE,
    outline_alpha: int = REGION_VOLUME_LABEL_OUTLINE_ALPHA,
) -> None:
    half_y = float(region.size[1]) * 0.5
    local_top = np.array([0.0, half_y, 0.0], dtype=np.float32)
    world_top = region.rotation @ local_top + region.center
    pt = project_point(win, world_top)
    if pt is None:
        return
    sx, sy, _ = pt
    color_hex = color or DESELECTED_COLOR
    qcolor = QColor.fromRgbF(*hex_to_rgb(color_hex))
    qcolor.setAlphaF(REGION_VOLUME_LABEL_TEXT_ALPHA_F)
    font = make_font()
    font.setPixelSize(pixel_size)
    font.setBold(bold)
    painter.setFont(font)

    outline = QColor.fromRgbF(*hex_to_rgb(REGION_VOLUME_LABEL_OUTLINE_COLOR))
    outline.setAlpha(outline_alpha)
    painter.setPen(outline)
    painter.drawText(
        int(sx) + 1, int(sy) - REGION_VOLUME_LABEL_Y_OFFSET + 1, text)
    painter.setPen(qcolor)
    painter.drawText(int(sx), int(sy) - REGION_VOLUME_LABEL_Y_OFFSET, text)
