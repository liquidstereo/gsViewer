import re
from pathlib import Path

def natural_sort_key(path: Path) -> tuple:
    return tuple(
        int(c) if c.isdigit() else c.lower()
        for c in re.split(r'(\d+)', path.name)
    )

def natural_sorted(paths) -> list[Path]:
    return sorted(paths, key=natural_sort_key)
