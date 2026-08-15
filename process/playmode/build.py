import random
from pathlib import Path

def build_ordered_segments(
    input_specs: list[tuple[str, list[Path]]],
    mode: str,
    seed: int | None = None,
) -> tuple[list[Path], list[tuple[str, int, int]]]:
    order = list(range(len(input_specs)))
    if mode == 'shuffle':
        random.Random(seed).shuffle(order)
    all_files: list[Path] = []
    segments: list[tuple[str, int, int]] = []
    start = 0
    for oi in order:
        iid, files = input_specs[oi]
        segments.append((iid, start, len(files)))
        all_files.extend(files)
        start += len(files)
    return all_files, segments
