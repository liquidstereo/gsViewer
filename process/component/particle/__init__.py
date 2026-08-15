from process.component.particle.plugin import ParticlePlugin

PLUGIN_NAME: str = 'particle'
REQUIRES: list[str] = []

def create_plugin(**kwargs) -> ParticlePlugin:
    return ParticlePlugin()

__all__ = ['ParticlePlugin', 'PLUGIN_NAME', 'REQUIRES', 'create_plugin']
