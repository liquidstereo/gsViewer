from plugins.noise.plugin import NoisePlugin

PLUGIN_NAME: str = 'noise'
REQUIRES: list[str] = []
REQUIRES_PLUGINS: list[str] = []

CONFLICTS: list[str] = ['particle']

def create_plugin(**kwargs) -> NoisePlugin:
    return NoisePlugin()

__all__ = [
    'NoisePlugin', 'PLUGIN_NAME', 'REQUIRES',
    'REQUIRES_PLUGINS', 'CONFLICTS', 'create_plugin',
]
