from process.common.scalarmath import clamp
from process.component.spring.engine import spring_step
from process.component.spring.settings import (
    DAMPING_RANGE, FREQ_RANGE, SNAP_DT,
)

def spring_eval(
    component, target: float, tick: int, key: tuple,
    freq: float | None = None, damping: float | None = None,
) -> float:
    state = component.states.get(key)
    if state is not None and state[2] == tick:
        return state[0]
    fps = float(getattr(component, 'fps', 0.0)) or 1.0
    dt = (float(tick) - float(state[2])) / fps if state is not None else 0.0
    if state is None or dt <= 0.0 or dt > SNAP_DT:
        component.states[key] = (target, 0.0, tick)
        return target
    f = (component.freq if freq is None
         else clamp(float(freq), *FREQ_RANGE))
    d = (component.damping if damping is None
         else clamp(float(damping), *DAMPING_RANGE))
    y, v = spring_step(state[0], state[1], target, dt, f, d)
    component.states[key] = (y, v, tick)
    return y
