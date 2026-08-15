import torch

from process.widget.overlays.curve_model import CurveState, EASE_EASE

def flat_points(n: int) -> list:
    m = max(2, int(n))
    return [(i / (m - 1), 1.0, EASE_EASE) for i in range(m)]

class RampCurve:

    def __init__(self, default: list, n_points: int, lut_n: int) -> None:
        self._default: list = list(default)
        self.state: CurveState = CurveState(n_points, lut_n)
        self.state.set_points(self._default)
        self._cpu: torch.Tensor | None = None
        self._dev: torch.Tensor | None = None
        self._dev_key: tuple | None = None

    @property
    def points(self) -> list:
        return self.state.points

    def set_points(self, points: list) -> None:
        self.state.set_points(points)
        self._invalidate()

    def reset(self) -> None:
        self.state.set_points(self._default)
        self._invalidate()

    def _invalidate(self) -> None:
        self._cpu = None
        self._dev = None
        self._dev_key = None

    def _lut_for(self, ref: torch.Tensor) -> torch.Tensor:
        if self._cpu is None:
            self._cpu = torch.as_tensor(
                self.state.lut(), dtype=torch.float32,
            )
        key = (ref.device, ref.dtype)
        if self._dev is None or self._dev_key != key:
            self._dev = self._cpu.to(device=ref.device, dtype=ref.dtype)
            self._dev_key = key
        return self._dev

    def evaluate(self, rv: torch.Tensor) -> torch.Tensor:
        lut = self._lut_for(rv)
        m = int(lut.shape[0])
        idx = torch.clamp(rv, 0.0, 1.0) * (m - 1)
        lo = idx.floor().long().clamp(0, m - 1)
        hi = (lo + 1).clamp(0, m - 1)
        frac = idx - lo.to(idx.dtype)
        return lut[lo] * (1.0 - frac) + lut[hi] * frac
