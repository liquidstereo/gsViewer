from typing import Callable

from process.widget.overlays import AttrSpec, KIND_CURVE, KIND_ENUM
from process.component.ramp.curve import flat_points
from process.component.ramp.state import RegionRampState
from process.component.ramp.settings import (
    REGION_RAMP_DEFAULT_SHAPE, REGION_RAMP_INTENSITY_HANDLES,
    REGION_RAMP_MULT_HANDLES, REGION_RAMP_SHAPES,
)

def ramp_specs(
    state: RegionRampState, commit: Callable[[], None],
) -> list:
    return [
        AttrSpec('Falloff', KIND_ENUM, lambda: state.ramp_shape,
                 lambda v: setattr(state, 'ramp_shape', v),
                 options=REGION_RAMP_SHAPES,
                 default=REGION_RAMP_DEFAULT_SHAPE,
                 tooltip=('Spatial ramp falloff shape: linear / '
                          'spherical / box.')),
        AttrSpec('Intensity', KIND_CURVE, lambda: state.intensity.points,
                 lambda pts: state.intensity.set_points(pts),
                 on_commit=commit,
                 default=flat_points(REGION_RAMP_INTENSITY_HANDLES),
                 tooltip='Effect strength multiplier ramp inside region.'),
        AttrSpec('Opacity', KIND_CURVE, lambda: state.opacity.points,
                 lambda pts: state.opacity.set_points(pts),
                 on_commit=commit,
                 default=flat_points(REGION_RAMP_MULT_HANDLES),
                 tooltip='Opacity multiplier ramp inside the region map.'),
        AttrSpec('Scale', KIND_CURVE, lambda: state.scale.points,
                 lambda pts: state.scale.set_points(pts),
                 on_commit=commit,
                 default=flat_points(REGION_RAMP_MULT_HANDLES),
                 tooltip='Scale multiplier ramp inside the region map.'),
    ]
