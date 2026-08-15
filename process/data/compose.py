import logging

import numpy as np
import torch

logger = logging.getLogger(__name__)

def _pad_sh(sh: torch.Tensor, target_k: int) -> torch.Tensor:
    if sh.shape[1] == target_k:
        return sh
    n, _, c = sh.shape
    pad = torch.zeros(
        n, target_k - sh.shape[1], c,
        dtype=sh.dtype, device=sh.device,
    )
    return torch.cat([sh, pad], dim=1)

def _concat_field(parts: list[dict], key: str) -> torch.Tensor | None:
    vals = [p[key] for p in parts if key in p]
    if len(vals) != len(parts):
        return None
    if not all(isinstance(v, torch.Tensor) for v in vals):
        return None
    return torch.cat(vals, dim=0)

def compose_splats(splats: dict) -> dict:
    keys = list(splats.keys())
    parts = [splats[k] for k in keys]
    device = parts[0]['means'].device
    ns = [p['means'].shape[0] for p in parts]
    src_ids = torch.cat([
        torch.full((n,), i, dtype=torch.int32, device=device)
        for i, n in enumerate(ns)
    ])
    if len(parts) == 1:
        out = dict(parts[0])
        out['_source_id'] = src_ids
        out['_source_keys'] = keys
        return out
    out: dict = {}
    for key in ('means', 'scales', 'quats', 'opacities', 'colors'):
        cat = _concat_field(parts, key)
        if cat is not None:
            out[key] = cat

    if all('sh_coeffs' in p for p in parts):
        max_k = max(p['sh_coeffs'].shape[1] for p in parts)
        padded = [_pad_sh(p['sh_coeffs'], max_k) for p in parts]
        out['sh_coeffs'] = torch.cat(padded, dim=0)

    if all('means_np' in p for p in parts):
        out['means_np'] = np.concatenate(
            [p['means_np'] for p in parts], axis=0,
        )
    out['_source_id'] = src_ids
    out['_source_keys'] = keys
    return out
