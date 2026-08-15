import logging

from process.common.help import register_help_section
from process.component.particle.keys import (
    handle_toggle_particles, handle_toggle_interactive,
    handle_particle_impulse,
)
from process.component.particle.settings import (
    PARTICLE_ENABLED,
    PARTICLE_KEY_TOGGLE, PARTICLE_KEY_INTERACT, PARTICLE_KEY_IMPULSE,
)
from process.component.particle.system import ParticleSystem

logger = logging.getLogger(__name__)

class ParticlePlugin:
    def __init__(self) -> None:
        self.particles: ParticleSystem = ParticleSystem()

    def attach(self, window) -> None:
        window._particles = self.particles
        window._particle_plugin = self
        window._frame_processors.append(self._process_frame)
        window._extra_handlers[PARTICLE_KEY_TOGGLE] = (
            handle_toggle_particles
        )
        window._extra_handlers[PARTICLE_KEY_INTERACT] = (
            handle_toggle_interactive
        )
        window._extra_handlers[PARTICLE_KEY_IMPULSE] = (
            handle_particle_impulse
        )
        register_help_section(window, 'PARTICLE', [
            (PARTICLE_KEY_TOGGLE, 'Burst VFX toggle'),
            (PARTICLE_KEY_INTERACT, 'Interactive mode'),
            (PARTICLE_KEY_IMPULSE, 'Impulse inject'),
        ])
        if PARTICLE_ENABLED:
            self.particles.reset(window._splat)
        logger.info('ParticlePlugin attached')

    def _process_frame(self, splat: dict) -> dict:
        if self.particles.active:
            return self.particles.step(splat)
        return splat
