import logging

logger = logging.getLogger(__name__)

_AXIS_IDX: dict[str, int] = {'X': 0, 'Y': 1, 'Z': 2}

def apply_clipping(
    splat: dict,
    axis: str,
    min_val: float,
    max_val: float,
) -> dict:
    idx = _AXIS_IDX[axis.upper()]
    coords = splat['means'][:, idx]
    mask = (coords >= min_val) & (coords <= max_val)
    clipped = dict(splat)
    clipped['opacities'] = (
        splat['opacities'] * mask.float()
    ).clamp(0.0, 1.0)
    logger.debug(
        'Clipping %s [%.2f, %.2f]: %d / %d points visible',
        axis, min_val, max_val,
        int(mask.sum().item()), int(mask.shape[0]),
    )
    return clipped
