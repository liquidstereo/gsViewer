import numpy as np
import torch

from process.component.region_volume.picking_shapes import ray_obb
from process.component.region_volume.region_solid_base import (
    RegionSolid, smoothstep,
)
from process.component.region_volume.polygon.geometry import (
    edge_distance_t, point_in_polygon_t, polygon_extents,
)
from process.component.region_volume.polygon.settings import POLYGON_MIN_VERTS

_MIN: float = 0.001
_EPS: float = 0.000001

class RegionPolygon(RegionSolid):

    _shape_name: str = 'polygon'
    _log_label: str = 'Polygon'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.verts2d: np.ndarray = np.zeros((0, 2), dtype=np.float32)
        self.committed: bool = False
        self._default_verts2d: np.ndarray = self.verts2d.copy()

    def set_polygon(
        self, verts2d: np.ndarray, center: np.ndarray,
        rotation: np.ndarray, depth: float,
    ) -> None:
        self.verts2d = np.asarray(verts2d, dtype=np.float32)
        su, sv = polygon_extents(self.verts2d)
        self.center = np.asarray(center, dtype=np.float32)
        self.rotation = np.asarray(rotation, dtype=np.float32)
        self.size = np.array([su, sv, max(float(depth), _MIN)],
                             dtype=np.float32)
        self.committed = True
        self._default_center = self.center.copy()
        self._default_size = self.size.copy()
        self._default_rotation = self.rotation.copy()
        self._default_verts2d = self.verts2d.copy()

    def mask(self, means: torch.Tensor) -> torch.Tensor:
        if not self.committed or len(self.verts2d) < POLYGON_MIN_VERTS:
            return torch.ones(
                means.shape[0], device=means.device, dtype=means.dtype)
        local, _ = self._locals(means)
        verts = torch.from_numpy(self.verts2d).to(
            means.device, means.dtype)
        lu, lv, ln = local[:, 0], local[:, 1], local[:, 2]
        half_d = float(self.size[2]) * 0.5
        inside_uv = point_in_polygon_t(lu, lv, verts)
        dist_uv = edge_distance_t(lu, lv, verts)
        signed_uv = torch.where(inside_uv, dist_uv, -dist_uv)
        dn = half_d - torch.abs(ln)
        signed = torch.minimum(signed_uv, dn)
        char = 0.5 * float(max(self.size[0], self.size[1], _MIN))
        band = float(max(self.softness, _EPS)) * char
        t = (signed / (2.0 * band) + 0.5).clamp(0.0, 1.0)
        return smoothstep(t)

    def scale_uniform(self, factor: float) -> None:
        if factor <= 0.0:
            return
        super().scale_uniform(factor)
        self.verts2d = (self.verts2d * float(factor)).astype(np.float32)

    def reset(self) -> None:
        super().reset()
        self.verts2d = self._default_verts2d.copy()

    def ray_hit(
        self, origin: np.ndarray, direction: np.ndarray,
    ) -> float | None:
        if not self.committed:
            return None
        return ray_obb(
            origin, direction, self.center, self.size * 0.5, self.rotation,
        )

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['verts2d'] = self.verts2d.tolist()
        data['committed'] = self.committed
        return data

    def from_dict(self, data: dict) -> None:
        super().from_dict(data)
        self.verts2d = np.array(
            data.get('verts2d', []), dtype=np.float32).reshape(-1, 2)
        self.committed = bool(data.get('committed', len(self.verts2d) >= 3))
        self._default_center = self.center.copy()
        self._default_size = self.size.copy()
        self._default_rotation = self.rotation.copy()
        self._default_verts2d = self.verts2d.copy()
