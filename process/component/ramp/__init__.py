from process.component.ramp.apply import apply_ramp_mult
from process.component.ramp.curve import RampCurve, flat_points
from process.component.ramp.field import (
    ramp_val, region_inside, to_local_norm,
)
from process.component.ramp.specs import ramp_specs
from process.component.ramp.state import RegionRampState

__all__ = [
    'RampCurve', 'RegionRampState', 'apply_ramp_mult', 'flat_points',
    'ramp_specs', 'ramp_val', 'region_inside', 'to_local_norm',
]
