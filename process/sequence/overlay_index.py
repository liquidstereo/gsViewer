def seq_overlay_index(
    preserve: bool, seq_idx: int, tick: int, image_total: int
) -> int:
    if image_total <= 0:
        return 0
    if preserve:
        return max(0, min(seq_idx, image_total - 1))
    return tick % image_total
