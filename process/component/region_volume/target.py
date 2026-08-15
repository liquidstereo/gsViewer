from typing import Protocol, runtime_checkable

import numpy as np

@runtime_checkable
class TransformTarget(Protocol):
    center: np.ndarray
    size: np.ndarray
    rotation: np.ndarray

    def corners(self) -> np.ndarray:
        ...

    def edges(self) -> list[tuple[np.ndarray, np.ndarray]]:
        ...

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        ...

def identity_rotation() -> np.ndarray:
    return np.eye(3, dtype=np.float32)
