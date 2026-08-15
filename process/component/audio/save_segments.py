from pathlib import Path

from configs.settings import PLAYBACK_FPS

def collect_save_segments(window, audio_map: dict, audio_path: str | None):
    if PLAYBACK_FPS <= 0:
        return None

    if getattr(window, '_play_order', None) is not None:
        return None
    segs = getattr(window, '_chain_segments', None)
    if segs and audio_map:
        out = []
        for iid, _start, length in segs:
            entry = audio_map.get(iid)
            path = entry[2] if entry is not None else None
            out.append((path, length / PLAYBACK_FPS))
        return out
    if getattr(window, '_scheduler', None) is not None:
        return None
    if not (audio_path and Path(audio_path).is_file()):
        return None

    if getattr(window, '_save_continuous', False):
        frames = max(1, getattr(window, '_total_frames', 1))
    else:
        frames = max(1, getattr(window, '_save_count', 0)
                     or getattr(window, '_total_frames', 1))
    return [(audio_path, frames / PLAYBACK_FPS)]
