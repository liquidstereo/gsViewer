from plugins.crop.plugin import CropPlugin

PLUGIN_NAME: str = 'crop'
REQUIRES: list[str] = []
REQUIRES_PLUGINS: list[str] = []

CONFLICTS: list[str] = ['particle']

def create_plugin(**kwargs) -> CropPlugin:
    return CropPlugin()

__all__ = [
    'CropPlugin', 'PLUGIN_NAME', 'REQUIRES',
    'REQUIRES_PLUGINS', 'CONFLICTS', 'create_plugin',
]
