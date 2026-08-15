import hashlib
import math

_DIGEST_BYTES = 8
_DIGEST_MAX = float(1 << (_DIGEST_BYTES * 8))
_GAUSS_SIGMA_DIV = 3.0
_EPS = 0.000000000001

def deterministic_unit(seed: float, *keys: object) -> float:
    raw = '|'.join([repr(seed), *map(repr, keys)]).encode('utf-8')
    digest = hashlib.sha256(raw).digest()
    value = int.from_bytes(digest[:_DIGEST_BYTES], 'big')
    return value / _DIGEST_MAX

def deterministic_float(
    seed: float, lo: float, hi: float, *keys: object
) -> float:
    return lo + deterministic_unit(seed, *keys) * (hi - lo)

def deterministic_int(
    seed: float, lo: int, hi: int, *keys: object
) -> int:
    return lo + int(deterministic_unit(seed, *keys) * (hi - lo + 1))

def deterministic_offset(seed: float, dist: int, *keys: object) -> int:
    if dist <= 0:
        return 0
    return int(deterministic_unit(seed, *keys) * (2 * dist + 1)) - dist

def deterministic_vec3(
    seed: float, dist: float, *keys: object
) -> tuple[float, float, float]:
    return (
        deterministic_float(seed, -dist, dist, *keys, 0),
        deterministic_float(seed, -dist, dist, *keys, 1),
        deterministic_float(seed, -dist, dist, *keys, 2),
    )

def jitter_frame_index(
    current: int, count: int, frame_dist: int,
    frame_length: int, seed: float,
) -> int:
    if count <= 1 or frame_dist <= 0:
        return max(0, min(count - 1, current))
    length = max(1, frame_length)
    group = current // length
    offset = deterministic_offset(seed, frame_dist, 'frame', group)
    return max(0, min(count - 1, current + offset))

def _clamp(value: float, lo: float, hi: float) -> float:

    return max(lo, min(hi, value))

def _smoothstep(e0: float, e1: float, x: float) -> float:
    if e1 <= e0:
        return 1.0 if x >= e0 else 0.0
    t = _clamp((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def shape_random_value(
    base: float, vmin: float, vmax: float, amount: float, gain: float,
    threshold: float, softness: float, seed: float, *keys: object,
) -> float:
    span = vmax - vmin
    if span <= 0.0 or amount <= 0.0:
        return _clamp(base, vmin, vmax)
    r = deterministic_unit(seed, *keys)
    s = 2.0 * r - 1.0
    g = deterministic_unit(seed, 'gate', *keys)
    gate = _smoothstep(threshold, min(1.0, threshold + softness), g)
    delta = amount * span * s * gain * gate
    return _clamp(base + delta, vmin, vmax)

def random_output_value(
    amount: float, gain: float, threshold: float, softness: float,
    seed: float, *keys: object,
) -> float:
    if amount <= 0.0:
        return 0.0
    r = deterministic_unit(seed, *keys)
    g = deterministic_unit(seed, 'gate', *keys)
    gate = _smoothstep(threshold, min(1.0, threshold + softness), g)
    return _clamp(amount * gain * r * gate, 0.0, 1.0)

def scale_output_value(amount: float, gain: float, value: float) -> float:
    if amount <= 0.0:
        return 0.0
    return _clamp(amount * gain * value, 0.0, 1.0)

def deterministic_gaussian(seed: float, *keys: object) -> float:
    u1 = max(deterministic_unit(seed, *keys, 'g0'), _EPS)
    u2 = deterministic_unit(seed, *keys, 'g1')
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

def random_eval(component, x: float, key: tuple) -> float:
    seed = float(component.seed)
    amount = float(component.amount)
    full = (*key, int(getattr(component, 'reroll', 0)))
    if component.mode == 'gaussian':
        g = deterministic_gaussian(seed, *full) * (x / _GAUSS_SIGMA_DIV)
        return _clamp(g, -x, x) * amount
    return deterministic_float(seed, -x, x, *full) * amount
