import logging

import numpy as np

logger = logging.getLogger(__name__)

class InputTransformTarget:

    def __init__(self, lo: np.ndarray, hi: np.ndarray) -> None:
        center = ((lo + hi) * 0.5).astype(np.float32)
        size = (hi - lo).astype(np.float32)
        self.pivot: np.ndarray = center.copy()
        self.initial_size: np.ndarray = size.copy()
        self.center: np.ndarray = center.copy()
        self.size: np.ndarray = size.copy()
        self.rotation: np.ndarray = np.eye(3, dtype=np.float32)
        self.point_count: int = 0

    def reset(self) -> None:
        self.center = self.pivot.copy()
        self.size = self.initial_size.copy()
        self.rotation = np.eye(3, dtype=np.float32)

    def is_identity(self) -> bool:
        if not np.allclose(self.center, self.pivot):
            return False
        if not np.allclose(self.size, self.initial_size):
            return False
        if not np.allclose(self.rotation, np.eye(3, dtype=np.float32)):
            return False
        return True

    def corners(self) -> np.ndarray:
        half = self.size * 0.5
        hx, hy, hz = float(half[0]), float(half[1]), float(half[2])
        local = np.array([
            [-hx, -hy, -hz], [+hx, -hy, -hz],
            [+hx, +hy, -hz], [-hx, +hy, -hz],
            [-hx, -hy, +hz], [+hx, -hy, +hz],
            [+hx, +hy, +hz], [-hx, +hy, +hz],
        ], dtype=np.float32)
        return local @ self.rotation.T + self.center

    def edges(self) -> list[tuple[np.ndarray, np.ndarray]]:
        c = self.corners()
        idx = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        return [(c[i], c[j]) for i, j in idx]

def aabb_from_means(means: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if means.size == 0:
        raise ValueError('Empty means array -- cannot compute AABB')
    lo = means.min(axis=0).astype(np.float32)
    hi = means.max(axis=0).astype(np.float32)
    return lo, hi
