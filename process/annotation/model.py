import json
import logging
from pathlib import Path

import numpy as np
from process.common.floatfmt import dumps_fixed

logger = logging.getLogger(__name__)

class Annotations:

    def __init__(self) -> None:
        self._items: list[dict] = []

    def count(self) -> int:
        return len(self._items)

    def items(self) -> list[dict]:
        return self._items

    def add(
        self, cam: dict, eye_pos: np.ndarray, label: str,
        duration: int = 0,
    ) -> int:
        pos = np.array(eye_pos, dtype=np.float64)
        self._items.append({
            'pos':       pos.copy(),
            'target':    cam['target'].astype(np.float64).copy(),
            'label':     label,
            'azimuth':   float(cam['azimuth']),
            'elevation': float(cam['elevation']),
            'distance':  float(cam['distance']),
            'duration':  int(duration),
        })
        logger.info(
            'Annotation added: %r at eye (%.2f, %.2f, %.2f)',
            label, float(pos[0]), float(pos[1]), float(pos[2]),
        )
        return len(self._items)

    def remove_last(self) -> bool:
        if not self._items:
            return False
        removed = self._items.pop()
        logger.info('Annotation removed: %r', removed['label'])
        return True

    def clear(self) -> None:
        self._items.clear()
        logger.info('Annotations cleared')

    def save(self, path: Path) -> None:
        if not self._items:
            if path.exists():
                path.unlink()
                logger.info('Annotation file removed: %s', path.name)
            return
        data = [
            {
                'pos':       item['pos'].tolist(),
                'target':    item.get('target', item['pos']).tolist(),
                'label':     item['label'],
                'azimuth':   item.get('azimuth', 0.0),
                'elevation': item.get('elevation', 0.0),
                'distance':  item.get('distance', 1.0),
                'duration':  int(item.get('duration', 0)),
            }
            for item in self._items
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            dumps_fixed(data, indent=2, ensure_ascii=False)
        )
        logger.info(
            'Annotations saved: %s (%d items)', path.name, len(data)
        )

    def load(self, path: Path) -> bool:
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text())
            self._items = [
                {
                    'pos': np.array(item['pos'], dtype=np.float64),
                    'target': np.array(
                        item.get('target', item['pos']),
                        dtype=np.float64,
                    ),
                    'label':     item['label'],
                    'azimuth':   float(item.get('azimuth', 0.0)),
                    'elevation': float(item.get('elevation', 0.0)),
                    'distance':  float(item.get('distance', 1.0)),
                    'duration':  int(item.get('duration', 0)),
                }
                for item in data
            ]
            logger.info(
                'Annotations loaded: %s (%d items)',
                path.name, len(self._items),
            )
            return True
        except Exception:
            logger.error(
                'Annotations load failed: %s', path, exc_info=True
            )
            return False
