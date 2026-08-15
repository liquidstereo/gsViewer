import logging

from process.component.particle.settings import PARTICLE_IMPULSE_FORCE

logger = logging.getLogger(__name__)

def handle_toggle_particles(win) -> None:
    ps = win._particles
    if ps.active and not ps.interactive:
        ps.deactivate()
    else:
        ps.reset(win._splat)
    win._render_current()
    logger.info('Particle VFX: %s', ps.active)

def handle_toggle_interactive(win) -> None:
    ps = win._particles
    if ps.active and ps.interactive:
        ps.deactivate()
    else:
        ps.reset_interactive(win._splat)
    win._render_current()
    logger.info('Interactive particles: %s', ps.active)

def handle_particle_impulse(win) -> None:
    ps = win._particles
    if not ps.active:
        ps.reset_interactive(win._splat)
    ps.add_impulse(PARTICLE_IMPULSE_FORCE)
    win._render_current()
    logger.info('Particle impulse (interactive=%s)', ps.interactive)
