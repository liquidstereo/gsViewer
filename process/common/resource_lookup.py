from pathlib import Path

DATA_NAME_SUFFIXES: tuple[str, ...] = ('_cply', '_splat', '_ply')

def build_name_candidates(
    input_name: str, suffixes: tuple[str, ...] = DATA_NAME_SUFFIXES,
) -> list[str]:
    base_name = input_name
    for suffix in suffixes:
        if input_name.endswith(suffix):
            base_name = input_name[:-len(suffix)]
            break
    candidates = [input_name]
    if base_name != input_name:
        candidates.append(base_name)
    for suffix in suffixes:
        cand = f'{base_name}{suffix}'
        if cand not in candidates:
            candidates.append(cand)
    return candidates

def resolve_named_resource(
    base_dir: Path,
    input_name: str,
    exts: tuple[str, ...],
    suffixes: tuple[str, ...] = DATA_NAME_SUFFIXES,
) -> Path | None:
    if not input_name:
        return None
    for cand in build_name_candidates(input_name, suffixes):
        p = base_dir / cand
        if p.exists():
            return p
        for ext in exts:
            pf = p.with_suffix(ext)
            if pf.exists():
                return pf
    return None
