import math

from configs.settings import PLAYBACK_FPS
from process.common.scalarmath import clamp, mix, normalize, smoothstep

def linear(x: float, x0: float, x1: float, v0: float, v1: float) -> float:
    return mix(v0, v1, normalize(x, x0, x1))

def ease(x: float, x0: float, x1: float, v0: float, v1: float) -> float:
    return mix(v0, v1, smoothstep(x0, x1, x))

def ease_in(x: float, x0: float, x1: float, v0: float, v1: float) -> float:
    u = normalize(x, x0, x1)
    return mix(v0, v1, u * u)

def ease_out(x: float, x0: float, x1: float, v0: float, v1: float) -> float:
    u = normalize(x, x0, x1)
    return mix(v0, v1, u * (2.0 - u))

def round_half_up(value: float) -> float:
    return float(math.floor(value + 0.5))

def step(edge: float, x: float) -> float:
    return 1.0 if x >= edge else 0.0

def pick(cond: float, a: float, b: float) -> float:
    return a if cond else b

def scalar_utils() -> dict:
    return {
        'clamp': clamp,
        'linear': linear,
        'ease': ease,
        'ease_in': ease_in,
        'ease_out': ease_out,
        'smoothstep': smoothstep,
        'step': step,
        'pick': pick,
        'sin': math.sin,
        'cos': math.cos,
        'sqrt': math.sqrt,
        'abs': abs,
        'min': min,
        'max': max,
        'pow': pow,
        'int': math.trunc,
        'round': round_half_up,
        'floor': math.floor,
        'ceil': math.ceil,
        'PI': math.pi,
    }

def scalar_namespace(window) -> dict:
    tick = float(getattr(window, '_anim_tick', 0) or 0)
    fps = float(PLAYBACK_FPS) or 1.0
    ns = scalar_utils()
    ns['t'] = tick / fps
    ns['frame'] = tick
    return ns
