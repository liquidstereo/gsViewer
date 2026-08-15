import logging
import time

from process.console.reload import dump_attrs, reapply_attrs
from process.component.region_volume import RegionBox
from plugins.crop.physics import apply_crop_mask
from plugins.crop import settings as cfg
from plugins.crop.settings import STARTUP_ACTIVE

logger = logging.getLogger(__name__)

_DEFAULT_MAP = {
    'invert': 'DEFAULT_CROP_INVERT',
    'softness': 'DEFAULT_CROP_REGION_SOFTNESS',
}

class CropSystem:

    def __init__(self, region: RegionBox) -> None:
        self.region: RegionBox = region

        self.active: bool = STARTUP_ACTIVE

        self.invert: bool = False
        self.apply_defaults(cfg)

    @property
    def softness(self) -> float:
        return float(self.region.softness)

    @softness.setter
    def softness(self, value: float) -> None:
        self.region.softness = float(value)

    def apply_defaults(self, module) -> None:
        reapply_attrs(self, module, _DEFAULT_MAP)

    def dump_defaults(self, module) -> None:
        dump_attrs(self, module, _DEFAULT_MAP)

    def has_effect(self) -> bool:
        return self.active

    def set_active(self, value: bool) -> None:
        self.active = value
        logger.info('Crop active: %s', value)

    def toggle_active(self) -> None:
        self.set_active(not self.active)

    def toggle_invert(self) -> None:
        self.invert = not self.invert
        logger.info('Crop invert: %s', self.invert)

    def reset(self) -> None:
        self.active = STARTUP_ACTIVE
        self.apply_defaults(cfg)
        logger.info('Crop state reset')

    def step(self, splat: dict) -> dict:
        if not self.active:
            return splat
        t0 = time.perf_counter()
        means = splat['means']
        mask = self.region.mask(means)
        out = dict(splat)
        out['opacities'] = apply_crop_mask(
            splat['opacities'], mask, self.invert,
        )
        logger.debug(
            'Crop step: invert=%s %d pts %.3fms',
            self.invert, int(means.shape[0]),
            (time.perf_counter() - t0) * 1000.0,
        )
        return out
