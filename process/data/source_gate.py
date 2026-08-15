import torch

_GATED_CHANNELS = (
    'means', 'opacities', 'scales', 'quats', 'colors', 'sh_coeffs',
)

def restore_disabled_rows(
    original: dict, effected: dict, disabled_idx: set,
    channels: tuple = _GATED_CHANNELS,
) -> dict:
    if effected is original or not disabled_idx:
        return effected
    sid = original.get('_source_id')
    if sid is None:
        return effected
    keep = torch.zeros_like(sid, dtype=torch.bool)
    for idx in disabled_idx:
        keep |= sid == idx
    if not bool(keep.any()):
        return effected
    out = dict(effected)
    for key in channels:
        new = effected.get(key)
        old = original.get(key)
        if new is None or old is None or new is old:
            continue
        if not torch.is_tensor(new) or new.shape[0] != sid.shape[0]:
            continue
        mask = keep
        while mask.dim() < new.dim():
            mask = mask.unsqueeze(-1)
        out[key] = torch.where(mask, old, new)
    return out
