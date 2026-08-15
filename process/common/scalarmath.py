def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def normalize(x: float, x0: float, x1: float) -> float:
    if x1 <= x0:
        return 1.0 if x >= x0 else 0.0
    return clamp((x - x0) / (x1 - x0), 0.0, 1.0)

def mix(v0: float, v1: float, u: float) -> float:
    return v0 + (v1 - v0) * u

def smoothstep(e0: float, e1: float, x: float) -> float:
    u = normalize(x, e0, e1)
    return u * u * (3.0 - 2.0 * u)
