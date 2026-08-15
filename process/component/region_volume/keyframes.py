import logging
from pathlib import Path

import numpy as np
from process.keyframe import read_keyframe_json, write_keyframe_json

logger = logging.getLogger(__name__)

class RegionVolumeKeyframes:

    def __init__(self) -> None:
        self._items: list[dict] = []
        self._cursor: int = -1

    def count(self) -> int:
        return len(self._items)

    def items(self) -> list[dict]:
        return self._items

    @staticmethod
    def _copy_item(item: dict) -> dict:
        return {
            'center':   np.asarray(
                item['center'], dtype=np.float32).copy(),
            'size':     np.asarray(item['size'], dtype=np.float32).copy(),
            'rotation': np.asarray(
                item['rotation'], dtype=np.float32).copy(),
            'softness': float(item['softness']),
            'label':    item['label'],
            'extra':    dict(item.get('extra', {})),
            'scalars':  dict(item.get('scalars', {})),
        }

    def snapshot(self) -> list[dict]:
        return [self._copy_item(it) for it in self._items]

    def set_items(self, items: list[dict]) -> None:
        self._items = [self._copy_item(it) for it in items]
        self._cursor = -1

    def cursor(self) -> int:
        return self._cursor

    def reset_cursor(self) -> None:
        self._cursor = -1

    def add(
        self,
        center: np.ndarray,
        size: np.ndarray,
        rotation: np.ndarray,
        softness: float,
        label: str,
        extra: dict | None = None,
        scalars: dict | None = None,
    ) -> int:
        item = {
            'center':   np.asarray(center, dtype=np.float32).copy(),
            'size':     np.asarray(size, dtype=np.float32).copy(),
            'rotation': np.asarray(rotation, dtype=np.float32).copy(),
            'softness': float(softness),
            'label':    label,
            'extra':    dict(extra) if extra else {},
            'scalars':  dict(scalars) if scalars else {},
        }
        self._items.append(item)
        logger.info(
            'RegionVolume keyframe added: %r (%d total)',
            label, len(self._items),
        )
        return len(self._items)

    def remove_last(self) -> bool:
        if not self._items:
            return False
        removed = self._items.pop()
        if self._cursor >= len(self._items):
            self._cursor = -1
        logger.info('RegionVolume keyframe removed: %r', removed['label'])
        return True

    def clear(self) -> None:
        self._items.clear()
        self._cursor = -1
        logger.info('RegionVolume keyframes cleared')

    def goto(self, delta: int) -> dict | None:
        n = len(self._items)
        if n == 0:
            return None
        if self._cursor == -1:
            self._cursor = 0 if delta > 0 else n - 1
        else:
            self._cursor = (self._cursor + delta) % n
        return self._items[self._cursor]

    def save(self, path: Path) -> None:
        data = [
            {
                'center':   item['center'].tolist(),
                'size':     item['size'].tolist(),
                'rotation': item['rotation'].tolist(),
                'softness': item['softness'],
                'label':    item['label'],
                'extra':    item.get('extra', {}),
                'scalars':  item.get('scalars', {}),
            }
            for item in self._items
        ]
        write_keyframe_json(path, data, 'RegionVolume', logger, len(data),
                            log_removed=True)

    def load(self, path: Path) -> bool:
        data = read_keyframe_json(path, 'RegionVolume', logger)
        if data is None:
            return False
        self._items = [
            {
                'center':   np.array(item['center'], dtype=np.float32),
                'size':     np.array(item['size'], dtype=np.float32),
                'rotation': np.array(item['rotation'], dtype=np.float32),
                'softness': float(item['softness']),
                'label':    item['label'],
                'extra':    dict(item.get('extra', {})),
                'scalars':  dict(item.get('scalars', {})),
            }
            for item in data
        ]
        self._cursor = -1
        logger.info(
            'RegionVolume keyframes loaded: %s (%d items)',
            path.name, len(self._items),
        )
        return True
