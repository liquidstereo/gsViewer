from pathlib import Path

def _coalesce_runs(positions: list) -> list:
    runs: list = []
    cur_iid = None
    start_local = 0
    prev_local = None
    run_len = 0
    started = False
    for pos in positions:
        if pos is None:
            iid, local = None, None
        else:
            iid, local = pos[0], pos[1]
        same = started and iid == cur_iid and (
            iid is None or (local is not None and local == prev_local + 1)
        )
        if same:
            run_len += 1
            prev_local = local
            continue
        if run_len > 0:
            runs.append((cur_iid, start_local, run_len))
        cur_iid = iid
        start_local = local if local is not None else 0
        prev_local = local
        run_len = 1
        started = True
    if run_len > 0:
        runs.append((cur_iid, start_local, run_len))
    return runs

def _resolve_path(
    iid, audio_map: dict, audio_path: str | None,
) -> str | None:
    if iid is None:
        return None
    entry = audio_map.get(iid) if audio_map else None
    if entry is not None:
        return entry[2]
    if audio_path and Path(audio_path).is_file():
        return audio_path
    return None

def build_live_segments(
    positions: list, audio_map: dict, audio_path: str | None, fps: int,
) -> list | None:
    if fps <= 0 or not positions:
        return None
    runs = _coalesce_runs(positions)
    if not runs:
        return None
    segments: list = []
    for iid, start_local, run_len in runs:
        dur = run_len / fps
        path = _resolve_path(iid, audio_map, audio_path)
        if path is not None:
            segments.append((path, dur, start_local / fps))
        else:
            segments.append((None, dur))
    if all(seg[0] is None for seg in segments):
        return None
    return segments
