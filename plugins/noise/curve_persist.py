from plugins.noise.system import NoiseSystem

def _dump_points(points: list) -> list:
    return [[float(p[0]), float(p[1]), p[2]] for p in points]

def dump_curves(system: NoiseSystem) -> dict:
    return {
        'intensity': _dump_points(system.curve.points),
        'opacity': _dump_points(system.opacity_curve.points),
        'scale': _dump_points(system.scale_curve.points),
    }

def load_curves(system: NoiseSystem, data: dict) -> None:
    if not data:
        return
    intensity = data.get('intensity')
    if intensity:
        system.set_ramp_points(intensity)
    opacity = data.get('opacity')
    if opacity:
        system.opacity_curve.set_points(opacity)
    scale = data.get('scale')
    if scale:
        system.scale_curve.set_points(scale)
