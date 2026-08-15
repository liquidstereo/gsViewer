import logging

import numpy as np
import torch

from process.transform.controller import InputTransformController
from process.transform.picking import quat_from_matrix
from process.transform.target import InputTransformTarget

logger = logging.getLogger(__name__)

_EPS: float = 0.000001

def _quat_mul(q1: torch.Tensor, q2: torch.Tensor) -> torch.Tensor:
    w1, x1, y1, z1 = q1[..., 0], q1[..., 1], q1[..., 2], q1[..., 3]
    w2, x2, y2, z2 = q2[..., 0], q2[..., 1], q2[..., 2], q2[..., 3]
    return torch.stack([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ], dim=-1)

def _vec_from_size_ratio(target: InputTransformTarget) -> np.ndarray:
    ratio = target.size / np.maximum(target.initial_size, _EPS)
    return ratio.astype(np.float32)

def _apply_to_input(
    splat: dict, mask: torch.Tensor, target: InputTransformTarget,
) -> dict:
    if target.is_identity():
        return splat
    means_old = splat.get('means')
    if means_old is None:
        return splat
    device = means_old.device
    dtype = means_old.dtype
    pivot = torch.as_tensor(target.pivot, device=device, dtype=dtype)
    translate = torch.as_tensor(
        target.center - target.pivot, device=device, dtype=dtype,
    )
    R = torch.as_tensor(target.rotation, device=device, dtype=dtype)
    scale_np = _vec_from_size_ratio(target)
    scale_vec = torch.as_tensor(scale_np, device=device, dtype=dtype)
    means = means_old.clone()
    rel = means[mask] - pivot
    scaled = rel * scale_vec
    rotated = scaled @ R.T
    means[mask] = rotated + pivot + translate
    new_splat = dict(splat)
    new_splat['means'] = means
    scales_old = splat.get('scales')
    scale_mean = float(scale_np.mean())
    if scales_old is not None and abs(scale_mean - 1.0) > _EPS:
        scales = scales_old.clone()
        scales[mask] = scales[mask] * scale_mean
        new_splat['scales'] = scales
    quats_old = splat.get('quats')
    if quats_old is None:
        return new_splat
    qR_np = quat_from_matrix(target.rotation)
    if abs(qR_np[0] - 1.0) < _EPS and float(np.linalg.norm(qR_np[1:])) < _EPS:
        return new_splat
    qR = torch.as_tensor(qR_np, device=device, dtype=quats_old.dtype)
    quats = quats_old.clone()
    quats[mask] = _quat_mul(qR.expand_as(quats[mask]), quats[mask])
    new_splat['quats'] = quats
    return new_splat

def _hide_input(splat: dict, mask: torch.Tensor) -> dict:
    opac_old = splat.get('opacities')
    if opac_old is None:
        return splat
    opac = opac_old.clone()
    opac[mask] = 0.0
    new_splat = dict(splat)
    new_splat['opacities'] = opac
    return new_splat

def _apply_point_scale(
    splat: dict, mask: torch.Tensor, mult: float,
) -> dict:
    if abs(mult - 1.0) <= _EPS:
        return splat
    scales_old = splat.get('scales')
    if scales_old is None:
        return splat
    scales = scales_old.clone()
    scales[mask] = scales[mask] * mult
    new_splat = dict(splat)
    new_splat['scales'] = scales
    return new_splat

def make_frame_processor(controller: InputTransformController):
    def _process(splat: dict) -> dict:
        source_id = splat.get('_source_id')
        source_keys = splat.get('_source_keys')
        means = splat.get('means')
        if means is None:
            return splat
        if source_id is None or source_keys is None:
            if len(controller.targets) == 0:
                controller.ensure_target('__primary__', means)
            target = controller.targets.get('__primary__')
            if target is not None:
                target.point_count = int(means.shape[0])
            out = splat
            mask = torch.ones(
                means.shape[0], dtype=torch.bool, device=means.device,
            )
            if target is not None and not target.is_identity():
                out = _apply_to_input(out, mask, target)
            out = _apply_point_scale(
                out, mask, controller.get_point_scale('__primary__'),
            )
            if (controller.is_hidden('__primary__')
                    or controller.is_bracket_mode('__primary__')):
                out = _hide_input(out, mask)
            return out
        if len(source_keys) == 1:

            input_id = source_keys[0]
            mask = torch.ones(
                means.shape[0], dtype=torch.bool, device=means.device,
            )
            target = controller.ensure_target(input_id, means)
            if target is not None:
                target.point_count = int(means.shape[0])
            out = splat
            if target is not None and not target.is_identity():
                out = _apply_to_input(out, mask, target)
            out = _apply_point_scale(
                out, mask, controller.get_point_scale(input_id),
            )
            if (controller.is_hidden(input_id)
                    or controller.is_bracket_mode(input_id)):
                out = _hide_input(out, mask)
            return out
        out = splat
        for idx, input_id in enumerate(source_keys):
            mask = (source_id == idx)
            if not bool(mask.any()):
                continue
            target = controller.ensure_target(input_id, means[mask])
            if target is not None:
                target.point_count = int(mask.sum().item())
            if target is not None and not target.is_identity():
                out = _apply_to_input(out, mask, target)
            out = _apply_point_scale(
                out, mask, controller.get_point_scale(input_id),
            )
            if (controller.is_hidden(input_id)
                    or controller.is_bracket_mode(input_id)):
                out = _hide_input(out, mask)
        return out
    return _process
