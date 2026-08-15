import logging
from typing import Any, Callable

import numpy as np
from PySide6.QtGui import QPainter

from process.component.region_volume.overlay import RegionPalette
from process.component.region_volume.overlay_capsule import make_capsule_painter
from process.component.region_volume.overlay_cone import make_cone_painter
from process.component.region_volume.overlay_cylinder import make_cylinder_painter
from process.component.region_volume.overlay_sphere import make_sphere_painter
from process.component.region_volume.overlay_torus import make_torus_painter
from process.component.region_volume.region import RegionBox
from process.component.region_volume.region_capsule import RegionCapsule
from process.component.region_volume.region_cone import RegionCone
from process.component.region_volume.region_cylinder import RegionCylinder
from process.component.region_volume.region_sphere import RegionSphere
from process.component.region_volume.region_torus import RegionTorus
from process.component.region_volume.polygon import RegionPolygon, make_polygon_painter

logger = logging.getLogger(__name__)

_SHAPE_SPHERE: str = 'sphere'
_SHAPE_CYLINDER: str = 'cylinder'
_SHAPE_CONE: str = 'cone'
_SHAPE_CAPSULE: str = 'capsule'
_SHAPE_TORUS: str = 'torus'
_SHAPE_POLYGON: str = 'polygon'

_NON_BOX_SHAPES: frozenset[str] = frozenset({
    _SHAPE_SPHERE, _SHAPE_CYLINDER, _SHAPE_CONE,
    _SHAPE_CAPSULE, _SHAPE_TORUS, _SHAPE_POLYGON,
})
_REGION_CLASSES: dict = {
    _SHAPE_SPHERE: RegionSphere,
    _SHAPE_CYLINDER: RegionCylinder,
    _SHAPE_CONE: RegionCone,
    _SHAPE_CAPSULE: RegionCapsule,
    _SHAPE_TORUS: RegionTorus,
    _SHAPE_POLYGON: RegionPolygon,
}

def make_region(
    shape: str,
    *,
    center: tuple[float, float, float] = (0.0, 0.0, 0.0),
    size: tuple[float, float, float] = (1.0, 1.0, 1.0),
    softness: float = 0.10,
) -> Any:
    cls = _REGION_CLASSES.get(shape)
    if cls is not None:
        return cls(center=center, size=size, softness=softness)
    return RegionBox(center=center, size=size, softness=softness)

def make_region_painter_override(
    shape: str, plugin: Any, window: Any,
    palette: RegionPalette | None = None,
) -> Callable[[QPainter, int, int, np.ndarray | None], None] | None:
    if shape == _SHAPE_SPHERE:
        return make_sphere_painter(plugin, window, palette)
    if shape == _SHAPE_CYLINDER:
        return make_cylinder_painter(plugin, window, palette)
    if shape == _SHAPE_CONE:
        return make_cone_painter(plugin, window, palette)
    if shape == _SHAPE_CAPSULE:
        return make_capsule_painter(plugin, window, palette)
    if shape == _SHAPE_TORUS:
        return make_torus_painter(plugin, window, palette)
    if shape == _SHAPE_POLYGON:
        return make_polygon_painter(plugin, window, palette)
    return None

def is_box_shape(shape: str) -> bool:
    return shape not in _NON_BOX_SHAPES
