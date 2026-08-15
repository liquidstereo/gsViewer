import logging
from typing import Callable

import numpy as np

from configs.settings_camera import WORLD_ROT
from process.overlay_coord_io import (
    from_display_center, from_display_euler, from_display_scale,
    to_display_center, to_display_euler, to_display_scale)

logger = logging.getLogger(__name__)

_DEFAULT_VEC_MAP = {
    'region_position': '{PREFIX}_POSITION',
    'region_scale': '{PREFIX}_SCALE',
    'region_rotate': '{PREFIX}_ROTATE',
}

_DEFAULT_ROT = np.array(WORLD_ROT, dtype=np.float32)

def vec_attr_map(prefix: str) -> dict:
    out: dict = {}
    for attr, tmpl in _DEFAULT_VEC_MAP.items():
        out[tmpl.replace('{PREFIX}', prefix)] = (attr, False)
    return out

class RegionTransformSystem:

    def __init__(self, region_getter: Callable[[], object]) -> None:
        self._get_region = region_getter

    @property
    def region_position(self) -> list:
        r = self._get_region()
        if r is None:
            return [0.0, 0.0, 0.0]
        return [float(v) for v in to_display_center(r.center)]

    @region_position.setter
    def region_position(self, value: list) -> None:
        r = self._get_region()
        if r is None:
            return
        r.center = from_display_center(
            np.asarray(value, dtype=np.float32))

    @property
    def region_scale(self) -> list:
        r = self._get_region()
        if r is None:
            return [1.0, 1.0, 1.0]
        return [float(v) for v in to_display_scale(r.size, r._default_size)]

    @region_scale.setter
    def region_scale(self, value: list) -> None:
        r = self._get_region()
        if r is None:
            return
        r.size = from_display_scale(
            np.asarray(value, dtype=np.float32), r._default_size)

    @property
    def region_rotate(self) -> list:
        r = self._get_region()
        if r is None:
            return [0.0, 0.0, 0.0]
        return [float(v) for v in to_display_euler(r.rotation, _DEFAULT_ROT)]

    @region_rotate.setter
    def region_rotate(self, value: list) -> None:
        r = self._get_region()
        if r is None:
            return
        r.rotation = from_display_euler(
            np.asarray(value, dtype=np.float32), _DEFAULT_ROT)
