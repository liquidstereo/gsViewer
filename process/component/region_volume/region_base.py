import json
import logging
from pathlib import Path

import numpy as np
import torch

from configs.settings_camera import WORLD_ROT
from process.component.region_volume.settings import (
    REGION_CENTER, REGION_SIZE, REGION_SOFTNESS,
)
from process.common.floatfmt import dumps_fixed

logger = logging.getLogger(__name__)

_MIN_SIZE: float = 0.001
_DEFAULT_ROT: np.ndarray = np.array(WORLD_ROT, dtype=np.float32)

_OBB_LOCAL: np.ndarray = np.array([
    [-1, -1, -1], [+1, -1, -1], [+1, +1, -1], [-1, +1, -1],
    [-1, -1, +1], [+1, -1, +1], [+1, +1, +1], [-1, +1, +1],
], dtype=np.float32)
_OBB_EDGE_IDX: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)

class RegionTransformBase:

    _shape_name: str | None = None
    _log_label: str = ''

    def __init__(
        self,
        center: tuple[float, float, float] = REGION_CENTER,
        size: tuple[float, float, float] = REGION_SIZE,
        softness: float = REGION_SOFTNESS,
    ) -> None:
        self.center: np.ndarray = np.array(center, dtype=np.float32)
        self.size: np.ndarray = np.array(size, dtype=np.float32)

        self.rotation: np.ndarray = _DEFAULT_ROT.copy()
        self.softness: float = float(softness)
        self._default_center: np.ndarray = self.center.copy()
        self._default_size: np.ndarray = self.size.copy()
        self._default_rotation: np.ndarray = self.rotation.copy()

    def _subject(self) -> str:
        return f'{self._log_label} region' if self._log_label else 'Region'

    def translate(self, dx: float, dy: float, dz: float) -> None:
        self.center += np.array([dx, dy, dz], dtype=np.float32)

    def scale_uniform(self, factor: float) -> None:
        if factor <= 0.0:
            return
        self.size = np.maximum(self.size * factor, _MIN_SIZE)

    def reset(self) -> None:
        self.center = self._default_center.copy()
        self.size = self._default_size.copy()
        self.rotation = self._default_rotation.copy()

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        raise NotImplementedError

    def corners(self) -> np.ndarray:
        local = _OBB_LOCAL * (self.size * 0.5)
        return local @ self.rotation.T + self.center

    def edges(self) -> list[tuple[np.ndarray, np.ndarray]]:
        c = self.corners()
        return [(c[i], c[j]) for i, j in _OBB_EDGE_IDX]

    def to_dict(self) -> dict:
        data: dict = {}
        if self._shape_name is not None:
            data['shape'] = self._shape_name
        data['center'] = self.center.tolist()
        data['size'] = self.size.tolist()
        data['rotation'] = self.rotation.tolist()
        data['softness'] = self.softness
        return data

    def from_dict(self, data: dict) -> None:
        self.center = np.array(data['center'], dtype=np.float32)
        self.size = np.array(data['size'], dtype=np.float32)
        rot = data.get('rotation')
        if rot is None:
            self.rotation = _DEFAULT_ROT.copy()
        else:
            self.rotation = np.array(rot, dtype=np.float32)
        self.softness = float(data.get('softness', self.softness))

    def save(self, path: Path) -> None:
        data = self.to_dict()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dumps_fixed(data, indent=2), encoding='utf-8')
            logger.info('%s saved: %s', self._subject(), path)
        except OSError as e:
            logger.warning('%s save failed: %s', self._subject(), e)

    def load(self, path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning('%s load failed: %s', self._subject(), e)
            return False
        self.from_dict(data)
        logger.info('%s loaded: %s', self._subject(), path)
        return True

    def delete_file(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
            logger.info('%s file removed: %s', self._subject(), path)
        except OSError as e:
            logger.warning('%s file remove failed: %s', self._subject(), e)
