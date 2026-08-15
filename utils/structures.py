import numpy as np
from dataclasses import dataclass

@dataclass
class GaussianBuffer:
    means: np.ndarray | None = None
    rotations: np.ndarray | None = None
    scales: np.ndarray | None = None
    opacity: np.ndarray | None = None
    sh_coeffs: np.ndarray | None = None

    @property
    def n_gaussians(self) -> int:
        return 0 if self.means is None else len(self.means)
