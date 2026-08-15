import logging
import math

import torch

from process.component.noise import (
    curl, fractal, perlin, simplex, turbulence, worley,
)

logger = logging.getLogger(__name__)

_NOISE_FN: dict[str, callable] = {
    'curl':       curl.apply,
    'perlin':     perlin.apply,
    'turbulence': turbulence.apply,
    'fractal':    fractal.apply,
    'worley':     worley.apply,
    'simplex':    simplex.apply,
}

NOISE_TYPES: tuple[str, ...] = tuple(_NOISE_FN.keys())

def distort(
    noise_type: str, means: torch.Tensor, t: float, level: float,
    gain: float, freq: float, speed: float, octaves: int,
    phases: torch.Tensor,
) -> torch.Tensor:
    if level <= 0.0 or gain <= 0.0:
        return means
    fn = _NOISE_FN.get(noise_type)
    if fn is None:
        logger.warning(
            'Unknown noise type "%s", fallback to curl', noise_type,
        )
        fn = curl.apply
    return fn(means, t, level, gain, freq, speed, octaves, phases)

def scalar(
    noise_type: str, t: float, freq: float = 1.0, speed: float = 1.0,
    octaves: int = 2, seed: float = 0.0,
) -> float:
    fn = _NOISE_FN.get(noise_type)
    if fn is None:
        return 0.5
    n_oct = max(1, int(octaves))
    gen = torch.Generator().manual_seed(int(abs(seed) * 1000.0) & 0x7fffffff)
    p0 = torch.rand((1, 3), generator=gen) * 10.0
    phases = torch.rand((n_oct, 3), generator=gen) * (2.0 * math.pi)
    out = fn(p0, t, 1.0, 1.0, freq, speed, n_oct, phases)
    v = float((out - p0)[0, 0])
    return 0.5 + 0.5 * math.tanh(v)

__all__ = ['distort', 'scalar', 'NOISE_TYPES']
