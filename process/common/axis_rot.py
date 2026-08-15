_AXIS_VEC: dict[str, tuple[float, float, float]] = {
    '+X': (1.0, 0.0, 0.0),
    '-X': (-1.0, 0.0, 0.0),
    '+Y': (0.0, 1.0, 0.0),
    '-Y': (0.0, -1.0, 0.0),
    '+Z': (0.0, 0.0, 1.0),
    '-Z': (0.0, 0.0, -1.0),
}

_TARGET_UP: tuple[float, float, float] = (0.0, 0.0, 1.0)
_TARGET_FORWARD: tuple[float, float, float] = (0.0, -1.0, 0.0)

_ORTHO_EPS: float = 0.000001

def _cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )

def _dot(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def build_world_rot(up: str, forward: str) -> tuple[tuple[float, ...], ...]:
    src_up = _AXIS_VEC[up]
    src_forward = _AXIS_VEC[forward]
    if abs(_dot(src_up, src_forward)) > _ORTHO_EPS:
        raise ValueError(
            f'up and forward must be orthogonal: {up}, {forward}'
        )
    src = (_cross(src_up, src_forward), src_up, src_forward)
    tgt = (_cross(_TARGET_UP, _TARGET_FORWARD), _TARGET_UP, _TARGET_FORWARD)
    return tuple(
        tuple(
            float(sum(tgt[k][i] * src[k][j] for k in range(3)))
            for j in range(3)
        )
        for i in range(3)
    )

def build_world_rot_presets(
    pairs: tuple[tuple[str, str], ...],
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    return tuple(build_world_rot(up, forward) for up, forward in pairs)
