import torch

from process.component.ramp.curve import RampCurve, flat_points
from process.component.ramp.field import (
    ramp_val, region_inside, to_local_norm,
)
from process.component.ramp.settings import (
    REGION_RAMP_AXIS_DEFAULT, REGION_RAMP_DEFAULT_SHAPE,
    REGION_RAMP_EDGE_DEFAULT, REGION_RAMP_INTENSITY_HANDLES,
    REGION_RAMP_LUT_N, REGION_RAMP_MULT_HANDLES,
)

class RegionRampState:

    def __init__(self) -> None:
        self.ramp_shape: str = REGION_RAMP_DEFAULT_SHAPE
        self.ramp_axis: int = REGION_RAMP_AXIS_DEFAULT
        self.ramp_edge: float = REGION_RAMP_EDGE_DEFAULT
        lut_n = REGION_RAMP_LUT_N
        self.intensity: RampCurve = RampCurve(
            flat_points(REGION_RAMP_INTENSITY_HANDLES),
            REGION_RAMP_INTENSITY_HANDLES, lut_n,
        )
        self.opacity: RampCurve = RampCurve(
            flat_points(REGION_RAMP_MULT_HANDLES),
            REGION_RAMP_MULT_HANDLES, lut_n,
        )
        self.scale: RampCurve = RampCurve(
            flat_points(REGION_RAMP_MULT_HANDLES),
            REGION_RAMP_MULT_HANDLES, lut_n,
        )
        self._key: tuple | None = None
        self._rv: torch.Tensor | None = None
        self._inside: torch.Tensor | None = None
        self._dist: torch.Tensor | None = None

    def terms(
        self, means: torch.Tensor, region: object,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        key = (
            means.data_ptr(), int(means.shape[0]), id(region),
            region.center.tobytes(), region.size.tobytes(),
            region.rotation.tobytes(),
            self.ramp_shape, int(self.ramp_axis), float(self.ramp_edge),
        )
        if key != self._key:
            local = to_local_norm(
                means, region.center, region.rotation, region.size,
            )
            self._rv = ramp_val(local, self.ramp_shape, int(self.ramp_axis))
            self._dist = ramp_val(local, 'spherical', 0)
            self._inside = region_inside(
                local, self.ramp_shape, self.ramp_edge,
            )
            self._key = key
        return self._rv, self._inside, self._dist

    def intensity_mult(self, rv: torch.Tensor) -> torch.Tensor:
        return self.intensity.evaluate(rv)

    def opacity_mult(self, rv: torch.Tensor) -> torch.Tensor:
        return self.opacity.evaluate(rv)

    def scale_mult(self, rv: torch.Tensor) -> torch.Tensor:
        return self.scale.evaluate(rv)

    def reset(self) -> None:
        self.ramp_shape = REGION_RAMP_DEFAULT_SHAPE
        self.ramp_axis = REGION_RAMP_AXIS_DEFAULT
        self.ramp_edge = REGION_RAMP_EDGE_DEFAULT
        self.intensity.reset()
        self.opacity.reset()
        self.scale.reset()
        self._key = None
        self._rv = None
        self._inside = None
        self._dist = None

    def dump(self) -> dict:
        return {
            'intensity': _dump_points(self.intensity.points),
            'opacity': _dump_points(self.opacity.points),
            'scale': _dump_points(self.scale.points),
        }

    def load(self, data: dict) -> None:
        if not data:
            return
        intensity = data.get('intensity')
        if intensity:
            self.intensity.set_points(intensity)
        opacity = data.get('opacity')
        if opacity:
            self.opacity.set_points(opacity)
        scale = data.get('scale')
        if scale:
            self.scale.set_points(scale)
        self._key = None

def _dump_points(points: list) -> list:
    return [[float(p[0]), float(p[1]), p[2]] for p in points]
