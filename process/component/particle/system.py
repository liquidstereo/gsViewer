import logging
import time
from typing import Callable

import torch

from process.component.particle.settings import (
    PARTICLE_FORCE, PARTICLE_GRAVITY_Y,
    PARTICLE_FADE_RATE, PARTICLE_DRAG, PARTICLE_DT_MAX,
    PARTICLE_SPRING_K, PARTICLE_DAMPING,
    PARTICLE_VEL_CLAMP, PARTICLE_IMPULSE_FORCE,
)
from process.component.particle.physics import (
    _init_velocities, _integrate, _fade, _spring_step,
)

logger = logging.getLogger(__name__)

class ParticleSystem:
    def __init__(self) -> None:
        self.active: bool = False
        self.interactive: bool = False
        self._means: torch.Tensor | None = None
        self._base_means: torch.Tensor | None = None
        self._base_scales: torch.Tensor | None = None
        self._base_opac: torch.Tensor | None = None
        self._vels: torch.Tensor | None = None
        self._elapsed: float = 0.0
        self._prev_ts: float | None = None
        self._level_provider: Callable[[], float] | None = None
        self._scale_modifier: (
            Callable[[torch.Tensor, float], torch.Tensor] | None
        ) = None
        self._interactive_reset_hooks: list[Callable[[], None]] = []
        self._deactivate_hooks: list[Callable[[], None]] = []

    def set_level_provider(
        self, fn: Callable[[], float] | None
    ) -> None:
        self._level_provider = fn

    def set_scale_modifier(
        self,
        fn: Callable[[torch.Tensor, float], torch.Tensor] | None,
    ) -> None:
        self._scale_modifier = fn

    def add_interactive_reset_hook(
        self, fn: Callable[[], None]
    ) -> None:
        self._interactive_reset_hooks.append(fn)

    def add_deactivate_hook(
        self, fn: Callable[[], None]
    ) -> None:
        self._deactivate_hooks.append(fn)

    def reset(self, splat: dict) -> None:
        self._means = splat['means'].clone()
        self._base_means = self._means
        self._base_opac = splat['opacities'].clone()
        self._vels = _init_velocities(self._means, PARTICLE_FORCE)
        self._elapsed = 0.0
        self._prev_ts = None
        self.active = True
        self.interactive = False
        logger.info(
            'Particle reset (explosion): %d points',
            int(self._means.shape[0]),
        )

    def reset_interactive(self, splat: dict) -> None:
        self._means = splat['means'].clone()
        self._base_means = splat['means'].clone()
        self._base_scales = splat['scales'].clone()
        self._base_opac = splat['opacities'].clone()
        self._vels = torch.zeros_like(self._means)
        self._elapsed = 0.0
        self._prev_ts = None
        self.active = True
        self.interactive = True
        for hook in self._interactive_reset_hooks:
            hook()
        logger.info(
            'Interactive reset: %d points',
            int(self._means.shape[0]),
        )

    def add_impulse(
        self, force: float = PARTICLE_IMPULSE_FORCE
    ) -> None:
        if not self.active or self._vels is None:
            return
        self._vels = self._vels + torch.randn_like(
            self._vels
        ) * force
        logger.info('Impulse applied: force=%.2f', force)

    def deactivate(self) -> None:
        self.active = False
        self.interactive = False
        self._means = None
        self._base_means = None
        self._base_scales = None
        self._base_opac = None
        self._vels = None
        for hook in self._deactivate_hooks:
            hook()
        logger.info('Particle system deactivated')

    def _dt(self) -> tuple[float, float]:
        t0 = time.perf_counter()
        if self._prev_ts is None:
            dt = 0.0
        else:
            dt = min(t0 - self._prev_ts, PARTICLE_DT_MAX)
        self._prev_ts = t0
        self._elapsed += dt
        return dt, t0

    def _interactive_step(self, splat: dict, dt: float, t0: float) -> dict:
        self._means, self._vels = _spring_step(
            self._means, self._base_means, self._vels, dt,
            PARTICLE_SPRING_K, PARTICLE_DAMPING,
            PARTICLE_GRAVITY_Y, PARTICLE_VEL_CLAMP,
        )
        lvl = self._level_provider() if self._level_provider else 0.0
        out = dict(splat)
        out['means'] = self._means
        if self._scale_modifier is not None:
            out['scales'] = self._scale_modifier(self._base_scales, lvl)
        logger.debug(
            'Interactive step: dt=%.4f lvl=%.3f %.3fms',
            dt, lvl, (time.perf_counter() - t0) * 1000.0,
        )
        return out

    def step(self, splat: dict) -> dict:
        if not self.active or self._means is None:
            return splat
        dt, t0 = self._dt()
        if self.interactive:
            return self._interactive_step(splat, dt, t0)
        self._means = _integrate(
            self._means, self._vels, dt, PARTICLE_GRAVITY_Y
        )
        self._vels = self._vels * PARTICLE_DRAG
        out = dict(splat)
        out['means'] = self._means
        out['opacities'] = _fade(
            self._base_opac, PARTICLE_FADE_RATE, self._elapsed
        )
        logger.debug(
            'Particle step: dt=%.4f elapsed=%.2f %.3fms',
            dt, self._elapsed,
            (time.perf_counter() - t0) * 1000.0,
        )
        return out
