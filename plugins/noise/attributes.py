from process.widget.overlays import (
    AttrSpec, KIND_CURVE, KIND_ENUM, KIND_FLOAT, KIND_INT,
)
from process.widget.overlays.curve_model import default_points
from process.component.region_volume import compose_specs, register_box_attr_section
from plugins.noise.settings import (
    DEFAULT_NOISE_FREQ, DEFAULT_NOISE_GAIN, DEFAULT_NOISE_OCTAVES,
    DEFAULT_NOISE_RAMP_SHAPE, DEFAULT_NOISE_SIZE_VAR, DEFAULT_NOISE_SPEED,
    DEFAULT_NOISE_THRESHOLD, DEFAULT_NOISE_TYPE, DEFAULT_NOISE_WIDTH,
    NOISE_FREQ_RANGE, NOISE_GAIN_RANGE, NOISE_NOISE_TYPES,
    NOISE_OCTAVES_RANGE, NOISE_RAMP_SHAPES, NOISE_SIZE_VAR_RANGE,
    NOISE_SPEED_RANGE, NOISE_WIDTH_RANGE, STARTUP_NOISE_CURVE_HANDLES,
    STARTUP_NOISE_RAMP_MULT_DEFAULT,
)

def build_specs(plugin) -> list:
    s = plugin.system
    commit = plugin.save_curves
    return [
        AttrSpec('Noise', KIND_ENUM, lambda: s.noise_type,
                 lambda v: setattr(s, 'noise_type', v),
                 options=NOISE_NOISE_TYPES, default=DEFAULT_NOISE_TYPE,
                 tooltip='Noise displacement type. Key [T]: cycle types.'),
        AttrSpec('Falloff', KIND_ENUM, lambda: s.ramp_shape,
                 lambda v: setattr(s, 'ramp_shape', v),
                 options=NOISE_RAMP_SHAPES, default=DEFAULT_NOISE_RAMP_SHAPE,
                 tooltip=('Spatial ramp falloff shape: linear / '
                          'spherical / box.')),
        AttrSpec('Intensity', KIND_CURVE, lambda: s.curve.points,
                 lambda pts: s.set_ramp_points(pts), on_commit=commit,
                 default=default_points(STARTUP_NOISE_CURVE_HANDLES),
                 tooltip=('Reveal transition curve. Drag points; '
                          'right-click to add/remove or set easing.')),
        AttrSpec('Threshold', KIND_FLOAT, lambda: s.threshold,
                 lambda v: setattr(s, 'threshold', float(v)), 0.0, 1.0,
                 default=DEFAULT_NOISE_THRESHOLD,
                 tooltip=('Reveal amount: 0=scattered, 1=restored. '
                          'Keys [O]: up, [I]: down.')),
        AttrSpec('Gain', KIND_FLOAT, lambda: s.gain,
                 lambda v: setattr(s, 'gain', float(v)), *NOISE_GAIN_RANGE,
                 default=DEFAULT_NOISE_GAIN,
                 tooltip='Displacement distance in world units.'),
        AttrSpec('Freq', KIND_FLOAT, lambda: s.freq,
                 lambda v: setattr(s, 'freq', float(v)), *NOISE_FREQ_RANGE,
                 default=DEFAULT_NOISE_FREQ,
                 tooltip='Spatial frequency: higher adds finer detail.'),
        AttrSpec('Speed', KIND_FLOAT, lambda: s.speed,
                 lambda v: setattr(s, 'speed', float(v)), *NOISE_SPEED_RANGE,
                 default=DEFAULT_NOISE_SPEED,
                 tooltip='Time flow speed of the scattered points.'),
        AttrSpec('Width', KIND_FLOAT, lambda: s.width,
                 lambda v: setattr(s, 'width', float(v)), *NOISE_WIDTH_RANGE,
                 default=DEFAULT_NOISE_WIDTH,
                 tooltip='Threshold smoothstep transition width.'),
        AttrSpec('Octaves', KIND_INT, lambda: s.octaves,
                 lambda v: setattr(s, 'octaves', int(v)),
                 *NOISE_OCTAVES_RANGE, fmt='{:.0f}',
                 default=DEFAULT_NOISE_OCTAVES,
                 tooltip='Noise octave count: more adds richer detail.'),
        AttrSpec('Size Var', KIND_FLOAT, lambda: s.size_var,
                 lambda v: setattr(s, 'size_var', float(v)),
                 *NOISE_SIZE_VAR_RANGE,
                 default=DEFAULT_NOISE_SIZE_VAR,
                 tooltip=('Splat size falloff by distance from region '
                          'center (0=off).')),
        AttrSpec('Opacity', KIND_CURVE, lambda: s.opacity_curve.points,
                 lambda pts: s.opacity_curve.set_points(pts),
                 on_commit=commit, default=STARTUP_NOISE_RAMP_MULT_DEFAULT,
                 tooltip='Opacity multiplier ramp inside the region map.'),
        AttrSpec('Scale', KIND_CURVE, lambda: s.scale_curve.points,
                 lambda pts: s.scale_curve.set_points(pts),
                 on_commit=commit, default=STARTUP_NOISE_RAMP_MULT_DEFAULT,
                 tooltip='Scale multiplier ramp inside the region map.'),
    ]

def register_attributes(window, plugin) -> None:
    register_box_attr_section(
        window, plugin, plugin.overlay_label,
        lambda: compose_specs(window, plugin, build_specs(plugin)),
        active=lambda: plugin.system.active,
    )
