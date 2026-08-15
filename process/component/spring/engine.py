import math

from process.component.spring.settings import (
    MAX_SUBSTEPS, SUBSTEP_DT, SUBSTEP_SAFETY,
)

def _substep_dt(freq: float, damping: float) -> float:

    scale = max(0.000001, float(freq) * (1.0 + 2.0 * float(damping)))
    return min(SUBSTEP_DT, SUBSTEP_SAFETY / scale)

def spring_step(
    y: float, v: float, target: float, dt: float, freq: float,
    damping: float,
) -> tuple[float, float]:
    if dt <= 0.0:
        return y, v
    steps = max(1, int(math.ceil(dt / _substep_dt(freq, damping))))
    steps = min(MAX_SUBSTEPS, steps)
    h = dt / steps
    w = 2.0 * math.pi * float(freq)
    k = w * w
    c = 2.0 * float(damping) * w
    for _ in range(steps):
        a = k * (target - y) - c * v
        v = v + a * h
        y = y + v * h
    return y, v
