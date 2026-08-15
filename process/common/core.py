import sys
from pathlib import Path

import numpy as np
from configs.system_resources import get_gpu_info

def truncate_string(s: str, limit: int = 78, reverse: bool = False) -> str:
    s = str(s) if s else ''
    if len(s) <= limit:
        return s
    return f'...{s[-limit:]}' if reverse else f'{s[:limit]}...'

def _cmap_fallback(
    t_np: np.ndarray, cmap_name: str
) -> np.ndarray:
    if cmap_name == 'gray':
        return np.stack([t_np, t_np, t_np], axis=-1).astype(np.float32)
    s = np.clip(2.0 * t_np, 0.0, 1.0)
    r2 = np.clip(2.0 * t_np - 1.0, 0.0, 1.0)
    r_ch = r2
    g_ch = np.where(t_np <= 0.5, s, 1.0 - r2)
    b_ch = 1.0 - s
    return np.stack([r_ch, g_ch, b_ch], axis=-1).astype(np.float32)

def apply_cmap(t, cmap_name: str):
    import torch
    t_np = t.clamp(0.0, 1.0).cpu().numpy()
    try:
        import matplotlib.cm as mcm
        rgb = mcm.get_cmap(cmap_name)(t_np)[:, :3].astype(np.float32)
    except ImportError:
        rgb = _cmap_fallback(t_np, cmap_name)
    return torch.from_numpy(rgb).to(t.device)

def display_name(win, input_id: str) -> str:
    if input_id == '__primary__':
        return str(getattr(win, '_active_id', input_id) or input_id)
    return str(input_id)

def lock_hide_suffix(hidden: bool, locked: bool) -> str:
    flags = []
    if hidden:
        flags.append('H')
    if locked:
        flags.append('L')
    return f' ({"/".join(flags)})' if flags else ''

def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def complement_hex(hex_color: str) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'#{255 - r:02X}{255 - g:02X}{255 - b:02X}'

def _dilate_mask(mask: np.ndarray, r: int = 2) -> np.ndarray:

    result = mask
    for _ in range(r):
        src = result
        out = src.copy()
        out[:-1] = np.maximum(out[:-1], src[1:])
        out[1:] = np.maximum(out[1:], src[:-1])
        out[:, :-1] = np.maximum(out[:, :-1], src[:, 1:])
        out[:, 1:] = np.maximum(out[:, 1:], src[:, :-1])
        result = out
    return result

def build_depth_mask(
    segs: list,
    gs_depth: np.ndarray,
    h: int,
    w: int,
) -> np.ndarray:
    seg_depth = np.full((h, w), np.inf, dtype=np.float32)
    for seg in segs:
        sx1, sy1, z1, sx2, sy2, z2 = seg
        if z1 <= 0 or z2 <= 0:
            continue
        n = max(abs(sx2 - sx1), abs(sy2 - sy1), 1)
        t = np.linspace(0.0, 1.0, n + 1)
        px = np.round(sx1 + t * (sx2 - sx1)).astype(np.int32)
        py = np.round(sy1 + t * (sy2 - sy1)).astype(np.int32)
        valid = (0 <= px) & (px < w) & (0 <= py) & (py < h)
        px_v, py_v, t_v = px[valid], py[valid], t[valid]
        z_interp = 1.0 / ((1.0 - t_v) / z1 + t_v / z2)
        np.minimum.at(seg_depth, (py_v, px_v), z_interp)

    has_seg = seg_depth < np.inf
    in_front = (gs_depth <= 0) | (seg_depth <= gs_depth)
    raw = np.where(has_seg & in_front, 1.0, 0.0).astype(np.float32)
    return _dilate_mask(raw, r=2)

def compute_gpu_ahead(
    est_frame_mb: float = 50.0,
    usage_ratio: float = 0.50,
    min_ahead: int = 30,
    max_ahead: int = 300,
) -> int:
    gpu = get_gpu_info()
    if gpu is None:
        return min_ahead
    avail_mb = (
        gpu['vram_total_gb'] - gpu['vram_used_gb']
    ) * 1024.0
    computed = int(avail_mb * usage_ratio / est_frame_mb)
    return max(min_ahead, min(max_ahead, computed))

def get_worker_count(fraction: float) -> int:
    import psutil
    cores = psutil.cpu_count(logical=False) or 1
    return max(1, int(cores * fraction))

def build_cache_config(no_cache: bool) -> dict:
    from configs.settings import SEQUENCE_CACHE
    enabled = not no_cache
    return {
        'use_disk_cache': enabled,
        'use_seq_cache': enabled and SEQUENCE_CACHE,
        'use_gpu_preload': enabled,
    }

def find_input_path_candidates(raw: str) -> Path | None:
    from configs.settings import INPUT_DIR, DATA_DIR
    p = Path(raw)
    if p.exists():
        return p
    for base in (DATA_DIR, INPUT_DIR):
        candidate = base / raw
        if candidate.exists():
            return candidate

    suffixes = ['_cply', '_splat', '_ply']
    for suffix in suffixes:
        raw_suffix = f'{raw}{suffix}'
        p_suffix = Path(raw_suffix)
        if p_suffix.exists():
            return p_suffix
        for base in (DATA_DIR, INPUT_DIR):
            candidate_suffix = base / raw_suffix
            if candidate_suffix.exists():
                return candidate_suffix
    return None

def resolve_input_path(raw: str) -> Path:
    from configs.colorize import Msg
    candidate = find_input_path_candidates(raw)
    if candidate is not None:
        return candidate
    Msg.Error(f'Input not found: "{raw}"', divide=False)
    sys.exit(1)

def build_json_session_key(
    input_ids: list[str], plugin_names: list[str] | None = None,
) -> str:
    ids = sorted({i for i in input_ids if i})
    plugs = sorted({p for p in (plugin_names or []) if p})
    parts = ids + plugs
    return '_'.join(parts) if parts else 'default'

def build_output_stem(primary_id: str, input_ids: list[str]) -> str:
    from configs.settings import ABBREVIATE_OUTPUT_FILENAME
    ids = [i for i in input_ids if i]
    if len(ids) <= 1:
        return primary_id
    if ABBREVIATE_OUTPUT_FILENAME:
        return f'{primary_id}_{len(ids) - 1}more'
    return '_'.join(ids)

def json_output_path(input_name: str, category: str, filename: str) -> Path:
    from configs.settings import JSON_DIR
    base = input_name or 'default'
    return JSON_DIR / base / category / filename

def json_root_path(input_name: str, filename: str) -> Path:
    from configs.settings import JSON_DIR
    base = input_name or 'default'
    return JSON_DIR / base / filename

