import logging

import numpy as np
import torch

from process.common.core import json_output_path
from process.component.region_volume.settings import (
    REGION_AUTOSIZE_ENABLE, REGION_AUTOSIZE_FACTOR, UNIFORM_SCALE,
)
from process.common.floatfmt import dumps_fixed

logger = logging.getLogger(__name__)

_AUTOSIZE_MIN_SIZE: float = 0.001

class RegionPathsMixin:

    def _json_slug(self) -> str:
        label = (self.overlay_label or 'region').strip().lower()
        return label.replace(' ', '_') or 'region'

    def init_paths(self, window) -> None:
        name = getattr(window, '_json_key', '') or 'default'
        slug = self._json_slug()
        self.region_path = json_output_path(
            name, slug, f'{self.region_basename}.json',
        )

        self._autosize_region(window)

        self._default_transform = self.region.to_dict()
        self.keyframes_path = json_output_path(
            name, slug, f'{self.keyframes_basename}.json',
        )
        self.keyframes.load(self.keyframes_path)
        self.curves_path = json_output_path(
            name, slug, f'{self.curves_basename}.json',
        )

    def relabel_paths(self, window) -> None:
        name = getattr(window, '_json_key', '') or 'default'
        slug = self._json_slug()
        self.region_path = json_output_path(
            name, slug, f'{self.region_basename}.json',
        )
        self.keyframes_path = json_output_path(
            name, slug, f'{self.keyframes_basename}.json',
        )
        self.curves_path = json_output_path(
            name, slug, f'{self.curves_basename}.json',
        )

    def _autosize_region(self, window) -> None:
        if not REGION_AUTOSIZE_ENABLE:
            return
        splat = getattr(window, '_splat', None)
        means = splat.get('means') if isinstance(splat, dict) else None
        if means is None or means.shape[0] == 0:
            return
        center = (means.amin(dim=0) + means.amax(dim=0)) * 0.5
        rot = torch.from_numpy(self.region._default_rotation).to(
            means.device, means.dtype,
        )
        local = (means - center) @ rot
        extent = local.amax(dim=0) - local.amin(dim=0)
        if UNIFORM_SCALE:

            extent = torch.full_like(extent, float(extent.max()))
        size = (extent * REGION_AUTOSIZE_FACTOR).clamp(min=_AUTOSIZE_MIN_SIZE)
        center_np = center.detach().cpu().numpy().astype(np.float32)
        size_np = size.detach().cpu().numpy().astype(np.float32)
        self.region.center = center_np
        self.region.size = size_np
        self.region._default_center = center_np.copy()
        self.region._default_size = size_np.copy()
        logger.info('Region autosized to data bbox: size=%s', size_np.tolist())

    def save_region(self) -> None:
        self.region.save(self.region_path)

    def curve_state(self) -> dict:
        return {}

    def apply_curve_state(self, state: dict) -> None:
        return None

    def save_curves(self) -> None:
        state = self.curve_state()
        path = self.curves_path
        if not state:
            if path.exists():
                path.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            dumps_fixed(state, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        logger.info('Curve state saved: %s', path.name)

    def delete_curves(self) -> None:
        path = self.curves_path
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning('Curve state remove failed: %s', e)
