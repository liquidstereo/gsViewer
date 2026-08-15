import argparse
import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import torch

from configs.settings import (
    ENABLE_STRIDE_SLICING,
    LOAD_PROGRESS_DECODE,
    OPACITY_PRUNE_ENABLED,
    OPACITY_PRUNE_THRESHOLD,
    SLICING_RATIO,
)
from process.common.natural_sort import natural_sorted
from process.files.ply import load_ply_raw

logger = logging.getLogger(__name__)

_SLICE_ENABLED: bool = ENABLE_STRIDE_SLICING
_SLICE_RATIO: float = SLICING_RATIO

def configure_slicing(enable: bool, ratio: float) -> None:
    global _SLICE_ENABLED, _SLICE_RATIO
    _SLICE_ENABLED = enable
    _SLICE_RATIO = ratio
    logger.info(
        'Stride slicing: enabled=%s ratio=%.3f', enable, ratio,
        extra={'overlay': False},
    )

def get_slice_ratio() -> float:
    return _SLICE_RATIO

_SUPPORTED_GLOBS: tuple[str, ...] = (
    '*.compressed.ply', '*.ply', '*.splat', '*.sog', '*.spz',
)

def collect_ply_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    seen: set[Path] = set()
    for pattern in _SUPPORTED_GLOBS:
        seen.update(path.glob(pattern))

    files = natural_sorted(seen)
    if not files:
        from configs.colorize import Msg
        Msg.Error(
            f'No supported files found in: "{path}"', divide=False
        )
        logger.error('No supported files found in: %s', path)
        sys.exit(1)
    logger.info('Collected %d files from %s', len(files), path)
    return files

def _parse_range(rng: str) -> tuple[int, int]:
    parts = rng.split('-')
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise argparse.ArgumentTypeError(
            f'Invalid range format: "{rng}" (expected START-END)'
        )
    return int(parts[0]), int(parts[1])

def apply_frame_range(
    files: list[Path], rng: str | None
) -> list[Path]:
    if rng is None:
        return files
    start, end = _parse_range(rng)
    sliced = files[start:end + 1]
    if not sliced:
        from configs.colorize import Msg
        Msg.Error(
            f'Range {start}-{end} out of bounds'
            f' (total: {len(files)} files)',
            divide=False,
        )
        logger.error(
            'Range %d-%d yields no files (total: %d)',
            start, end, len(files),
        )
        sys.exit(1)
    logger.info(
        'Range applied: frames %d-%d (%d files)',
        start, end, len(sliced),
    )
    return sliced

def _prune_by_opacity(raw: dict, thr: float) -> dict:
    opa = raw['opacity_logit'].astype(np.float32).reshape(-1)
    keep = (1.0 / (1.0 + np.exp(-opa))) > thr
    if keep.all():
        return raw
    out = dict(raw)
    for k in ('means_np', 'log_scales_np', 'quats_np',
              'opacity_logit', 'sh_coeffs'):
        out[k] = raw[k][keep]
    return out

def _apply_stride_slice(raw: dict, ratio: float) -> dict:
    if ratio <= 0.0:

        stride = max(1, raw['means_np'].shape[0])
    else:
        stride = max(1, round(1.0 / ratio))
    if stride <= 1:
        return raw
    n0 = raw['means_np'].shape[0]
    out = dict(raw)
    for k in ('means_np', 'log_scales_np', 'quats_np',
              'opacity_logit', 'sh_coeffs'):
        out[k] = raw[k][::stride]
    logger.info(
        'Stride slice: %d -> %d (stride=%d, ratio=%.3f)',
        n0, out['means_np'].shape[0], stride, ratio,
        extra={'overlay': False},
    )
    return out

def _prepare_raw(raw: dict) -> dict:

    if OPACITY_PRUNE_ENABLED:
        _n0 = raw['means_np'].shape[0]
        raw = _prune_by_opacity(raw, OPACITY_PRUNE_THRESHOLD)
        logger.debug(
            'Opacity prune: %d -> %d (thr=%.3f)',
            _n0, raw['means_np'].shape[0], OPACITY_PRUNE_THRESHOLD,
        )
    if _SLICE_ENABLED and _SLICE_RATIO < 1.0:
        raw = _apply_stride_slice(raw, _SLICE_RATIO)
    return raw

def _numpy_to_splat(
    raw: dict,
    cam_pos: torch.Tensor | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    def _to_gpu(arr: np.ndarray) -> torch.Tensor:
        return (
            torch.from_numpy(np.ascontiguousarray(arr))
            .pin_memory()
            .cuda()
        )

    raw = _prepare_raw(raw)
    means_np: np.ndarray = raw['means_np']
    extent_max = float(
        (means_np.max(axis=0) - means_np.min(axis=0)).max()
    )
    log_scale_cap = float(np.log(max(extent_max, 0.000001)))
    log_scales_clipped = np.clip(
        raw['log_scales_np'], None, log_scale_cap,
    )
    scales = _to_gpu(np.exp(log_scales_clipped))
    quats = torch.nn.functional.normalize(
        _to_gpu(raw['quats_np']), p=2, dim=-1
    )
    opacities = torch.sigmoid(_to_gpu(raw['opacity_logit']))
    if on_progress is not None:
        on_progress(LOAD_PROGRESS_DECODE)
    means = _to_gpu(raw['means_np'])
    if on_progress is not None:
        on_progress(0.5)

    sh_coeffs = _to_gpu(raw['sh_coeffs']).float()
    if on_progress is not None:
        on_progress(1.0)
    result = {
        'means': means,
        'means_np': raw['means_np'],
        'scales': scales,
        'quats': quats,
        'opacities': opacities,
        'sh_coeffs': sh_coeffs,
    }
    if cam_pos is not None:
        from process.renderer.core import compute_colors
        result['colors'] = compute_colors(result, cam_pos)
    return result

def build_cpu_splat(raw: dict) -> dict:
    t0 = time.perf_counter()
    raw = _prepare_raw(raw)
    means_np: np.ndarray = raw['means_np']
    extent_max = float(
        (means_np.max(axis=0) - means_np.min(axis=0)).max()
    )
    log_scale_cap = float(np.log(max(extent_max, 0.000001)))
    scales_np = np.exp(np.clip(raw['log_scales_np'], None, log_scale_cap))

    def _to_cpu(arr: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(np.ascontiguousarray(arr))

    result = {
        'means': _to_cpu(raw['means_np']),
        'means_np': raw['means_np'],
        'scales': _to_cpu(scales_np),
        'quats': _to_cpu(raw['quats_np']),
        'opacities': _to_cpu(raw['opacity_logit']),
        'sh_coeffs': _to_cpu(raw['sh_coeffs']),
    }
    logger.debug(
        'build_cpu_splat: %d pts in %.1f ms',
        means_np.shape[0], (time.perf_counter() - t0) * 1000.0,
    )
    return result

def _load_with_cache(
    path: Path,
    use_cache: bool,
    parser: Callable[[Path, Callable[[float], None] | None], dict],
    label: str,
    on_progress: Callable[[float], None] | None = None,
) -> dict:

    t0 = time.perf_counter()
    from process.data.cache import load_cached, save_cache_async
    if use_cache:
        cached = load_cached(path, on_progress)
        if cached is not None:
            logger.debug(
                'Frame load (disk cache): %s in %.1fs',
                path.name, time.perf_counter() - t0,
            )
            return cached
    raw = parser(path, on_progress)
    if use_cache:
        save_cache_async(path, raw)
    logger.debug(
        'Frame load (%s): %s in %.1fs',
        label, path.name, time.perf_counter() - t0,
    )
    return raw

def _load_cply_cached(
    path: Path,
    use_cache: bool,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    from process.files.cply import load_cply_frame
    return _load_with_cache(
        path, use_cache, load_cply_frame, 'cply', on_progress
    )

def _load_sog_cached(
    path: Path,
    use_cache: bool,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    from process.files.sog import load_sog_frame
    return _load_with_cache(
        path, use_cache, load_sog_frame, 'SOG', on_progress
    )

def load_frame(
    path: Path,
    use_cache: bool = True,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    suffix = path.suffix.lower()
    if path.name.endswith('.compressed.ply'):
        result = _load_cply_cached(path, use_cache, on_progress)
    elif suffix == '.sog':
        result = _load_sog_cached(path, use_cache, on_progress)
    elif suffix == '.splat':
        from process.files.splat import load_splat_frame
        result = load_splat_frame(path, on_progress)
    elif suffix == '.spz':
        from process.files.spz import load_spz_frame
        result = load_spz_frame(path, on_progress)
    else:

        return load_ply_frame(path, use_cache, on_progress)
    if on_progress is not None:
        on_progress(1.0)
    return result

def load_ply_frame(
    ply_path: Path,
    use_cache: bool = True,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    t0 = time.perf_counter()
    if use_cache:
        from process.data.cache import load_cached, save_cache_async
        cached = load_cached(ply_path, on_progress)
        if cached is not None:
            logger.debug(
                'Frame load (disk cache): %s in %.1fs',
                ply_path.name, time.perf_counter() - t0,
            )
            return cached
        raw = load_ply_raw(ply_path, on_progress)
        save_cache_async(ply_path, raw)
        logger.debug(
            'Frame load (PLY + cache write): %s in %.1fs',
            ply_path.name, time.perf_counter() - t0,
        )
        return raw
    raw = load_ply_raw(ply_path, on_progress)
    logger.debug(
        'Frame load (PLY no-cache): %s in %.1fs',
        ply_path.name, time.perf_counter() - t0,
    )
    return raw
