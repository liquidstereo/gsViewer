from process.widget.overlays import AttrSpec, KIND_ENUM
from process.component.region_volume import compose_specs, register_box_attr_section

_MODE_INSIDE = 'inside'
_MODE_OUTSIDE = 'outside'

def _get_mode(system) -> str:
    return _MODE_OUTSIDE if system.invert else _MODE_INSIDE

def _set_mode(system, value: str) -> None:
    system.invert = (value == _MODE_OUTSIDE)

def build_specs(plugin) -> list:
    system = plugin.system
    return [
        AttrSpec('Mode', KIND_ENUM, lambda: _get_mode(system),
                 lambda v: _set_mode(system, v),
                 options=(_MODE_INSIDE, _MODE_OUTSIDE), default=_MODE_INSIDE,
                 tooltip=('Crop mode: inside keeps the region, outside '
                          'keeps the rest. Key [T]: toggle.')),
    ]

def register_attributes(window, plugin) -> None:
    register_box_attr_section(
        window, plugin, plugin.overlay_label,
        lambda: compose_specs(window, plugin, build_specs(plugin)),
        active=lambda: plugin.system.active,
    )
