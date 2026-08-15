import logging
import time

import torch

from process.component.noise import distort as noise_distort
from process.component.noise.phase import ensure_phases
from plugins.noise.physics import (
    apply_displacement, apply_opacity_gate,
    apply_scale_gate, apply_size_variability,
)
from process.common.wall_clock import clamped_wall_dt
from process.console.reload import dump_attrs, reapply_attrs
from process.widget.overlays.curve_model import CurveState
from plugins.noise import settings as cfg
from plugins.noise.ramp import reveal_from_curve
from plugins.noise.settings import (
    STARTUP_ACTIVE, STARTUP_NOISE_CURVE_HANDLES, STARTUP_NOISE_CURVE_LUT_N,
    STARTUP_NOISE_DT_MAX, STARTUP_NOISE_RAMP_MULT_DEFAULT,
    STARTUP_NOISE_RAMP_MULT_HANDLES,
)
from process.component.region_volume import RegionBox
from process.component.ramp import (
    RampCurve, apply_ramp_mult, ramp_val, region_inside, to_local_norm,
)

logger = logging.getLogger(__name__)

_DEFAULT_MAP = {
    'noise_type': 'DEFAULT_NOISE_TYPE',
    'threshold': 'DEFAULT_NOISE_THRESHOLD',
    'gain': 'DEFAULT_NOISE_GAIN',
    'freq': 'DEFAULT_NOISE_FREQ',
    'speed': 'DEFAULT_NOISE_SPEED',
    'octaves': 'DEFAULT_NOISE_OCTAVES',
    'ramp_shape': 'DEFAULT_NOISE_RAMP_SHAPE',
    'ramp_axis': 'DEFAULT_NOISE_RAMP_AXIS',
    'width': 'DEFAULT_NOISE_WIDTH',
    'min_opacity': 'DEFAULT_NOISE_MIN_OPACITY',
    'size_min': 'DEFAULT_NOISE_SIZE_MIN',
    'size_var': 'DEFAULT_NOISE_SIZE_VAR',
    'size_var_edge_min': 'DEFAULT_NOISE_SIZE_VAR_EDGE_MIN',
    'ramp_edge': 'DEFAULT_NOISE_RAMP_EDGE',
}
_DEFAULT_INTS = ('octaves', 'ramp_axis')

class NoiseSystem:

    def __init__(self, region: RegionBox) -> None:
        self.region: RegionBox = region

        self.active: bool = STARTUP_ACTIVE

        self.apply_defaults(cfg)

        self.curve: CurveState = CurveState(
            STARTUP_NOISE_CURVE_HANDLES, STARTUP_NOISE_CURVE_LUT_N)
        self._curve_lut_cpu: torch.Tensor | None = None
        self._curve_dev: torch.Tensor | None = None
        self._curve_dev_key: tuple | None = None

        self.opacity_curve: RampCurve = RampCurve(
            STARTUP_NOISE_RAMP_MULT_DEFAULT, STARTUP_NOISE_RAMP_MULT_HANDLES,
            STARTUP_NOISE_CURVE_LUT_N,
        )
        self.scale_curve: RampCurve = RampCurve(
            STARTUP_NOISE_RAMP_MULT_DEFAULT, STARTUP_NOISE_RAMP_MULT_HANDLES,
            STARTUP_NOISE_CURVE_LUT_N,
        )
        self._phases: torch.Tensor | None = None

        self._t: float = 0.0
        self._prev_ts: float | None = None

        self._static_key: tuple | None = None
        self._static_mask: torch.Tensor | None = None
        self._static_rv: torch.Tensor | None = None
        self._static_dist: torch.Tensor | None = None
        self._static_inside: torch.Tensor | None = None

    def has_effect(self) -> bool:
        return self.active

    def set_active(self, value: bool) -> None:
        self.active = value
        logger.info('Noise active: %s', value)

    def toggle_active(self) -> None:
        self.set_active(not self.active)

    def adjust_threshold(self, delta: float) -> float:
        self.threshold = float(min(1.0, max(0.0, self.threshold + delta)))
        return self.threshold

    def apply_defaults(self, module) -> None:
        reapply_attrs(self, module, _DEFAULT_MAP, _DEFAULT_INTS)
        soft = getattr(module, 'DEFAULT_NOISE_REGION_SOFTNESS', None)
        if soft is not None:
            self.region.softness = float(soft)

    def dump_defaults(self, module) -> None:
        dump_attrs(self, module, _DEFAULT_MAP)
        if hasattr(module, 'DEFAULT_NOISE_REGION_SOFTNESS'):
            module.DEFAULT_NOISE_REGION_SOFTNESS = float(self.region.softness)

    def reset(self) -> None:
        self.active = STARTUP_ACTIVE
        self.apply_defaults(cfg)
        self.curve.reset()
        self._curve_lut_cpu = None
        self._curve_dev = None
        self._curve_dev_key = None
        self.opacity_curve.reset()
        self.scale_curve.reset()
        self._t = 0.0
        self._prev_ts = None
        logger.info('Noise state reset')

    def set_ramp_points(self, points: list) -> None:
        self.curve.set_points(points)
        self._curve_lut_cpu = None
        self._curve_dev = None
        self._curve_dev_key = None

    def _curve_for(self, ref: torch.Tensor) -> torch.Tensor:
        if self._curve_lut_cpu is None:
            self._curve_lut_cpu = torch.as_tensor(
                self.curve.lut(), dtype=torch.float32,
            )
        key = (ref.device, ref.dtype)
        if self._curve_dev is None or self._curve_dev_key != key:
            self._curve_dev = self._curve_lut_cpu.to(
                device=ref.device, dtype=ref.dtype,
            )
            self._curve_dev_key = key
        return self._curve_dev

    def _advance_clock(self) -> None:
        dt, self._prev_ts = clamped_wall_dt(
            self._prev_ts, STARTUP_NOISE_DT_MAX)
        self._t += max(0.0, dt)

    def _static_terms(
        self, means: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        region = self.region
        key = (
            means.data_ptr(), int(means.shape[0]), id(region),
            region.center.tobytes(), region.size.tobytes(),
            region.rotation.tobytes(), float(region.softness),
            self.ramp_shape, int(self.ramp_axis), float(self.ramp_edge),
        )
        if key != self._static_key:
            self._static_mask = region.mask(means)
            local = to_local_norm(
                means, region.center, region.rotation, region.size,
            )
            self._static_rv = ramp_val(
                local, self.ramp_shape, int(self.ramp_axis),
            )
            self._static_dist = ramp_val(local, 'spherical', 0)
            self._static_inside = region_inside(
                local, self.ramp_shape, self.ramp_edge,
            )
            self._static_key = key
        return (
            self._static_mask, self._static_rv,
            self._static_dist, self._static_inside,
        )

    def _ensure_phases(self, ref: torch.Tensor) -> torch.Tensor:
        self._phases = ensure_phases(self._phases, self.octaves, ref)
        return self._phases

    def step(self, splat: dict) -> dict:
        if not self.active:
            self._prev_ts = None
            return splat
        t0 = time.perf_counter()
        self._advance_clock()
        means = splat['means']
        phases = self._ensure_phases(means)
        distorted = noise_distort(
            self.noise_type, means, self._t, 1.0,
            self.gain, self.freq,
            self.speed, int(self.octaves), phases,
        )
        offset = distorted - means
        region_mask, rv, dist, inside = self._static_terms(means)
        reveal = reveal_from_curve(
            rv, self._curve_for(rv), self.threshold, self.width,
        )
        out = dict(splat)
        out['means'] = apply_displacement(
            means, offset, (1.0 - reveal) * region_mask,
        )
        opac = apply_opacity_gate(
            splat['opacities'], region_mask, reveal,
            self.min_opacity,
        )
        out['opacities'] = apply_ramp_mult(
            opac, inside, self.opacity_curve.evaluate(rv),
        )
        if 'scales' in splat:
            scales = apply_size_variability(
                splat['scales'], region_mask, dist, self.size_var,
                self.size_var_edge_min,
            )
            scales = apply_ramp_mult(
                scales, inside, self.scale_curve.evaluate(rv),
            )
            out['scales'] = apply_scale_gate(
                scales, region_mask, reveal, self.size_min,
            )
        logger.debug(
            'Noise step: type=%s thr=%.2f %d pts %.3fms',
            self.noise_type, self.threshold, int(means.shape[0]),
            (time.perf_counter() - t0) * 1000.0,
        )
        return out
