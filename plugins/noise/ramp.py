import torch

def reveal_from_curve(
    rv: torch.Tensor, curve: torch.Tensor,
    threshold: float, width: float,
) -> torch.Tensor:
    pan = (threshold - 0.5) * (1.0 + 2.0 * width)
    u = torch.clamp(rv - pan, 0.0, 1.0)
    m = int(curve.shape[0])
    idx = u * (m - 1)
    lo = idx.floor().long().clamp(0, m - 1)
    hi = (lo + 1).clamp(0, m - 1)
    frac = idx - lo.to(idx.dtype)
    c = curve[lo] * (1.0 - frac) + curve[hi] * frac
    return 1.0 - c
