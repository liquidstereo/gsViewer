import hashlib
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from configs.settings import (
    INPUT_DIR, DATA_DIR, CACHE_DIR, CACHE_HASH_CHUNK_BYTES,
    CACHING_METHOD,
)

logger = logging.getLogger(__name__)

_pending_lock = threading.Lock()
_pending_saves: set[threading.Thread] = set()

_CACHE_KEYS = (
    'means_np', 'log_scales_np', 'quats_np',
    'opacity_logit', 'sh_coeffs',
)
_SH_BANDS: int = 16

_KIND_GAUSSIAN: str = 'gaussian'
_KIND_POINTCLOUD: str = 'pointcloud'
_POINTCLOUD_KEYS = ('means_np', 'colors_np')

def _md5(
    path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> str:
    h = hashlib.md5()
    total = path.stat().st_size
    loaded = 0
    with open(path, 'rb') as f:
        for chunk in iter(
                lambda: f.read(CACHE_HASH_CHUNK_BYTES), b''):
            h.update(chunk)
            loaded += len(chunk)
            if on_progress and total > 0:
                on_progress(loaded / total)
    return h.hexdigest()

def _file_meta(path: Path) -> tuple[int, int]:

    st = path.stat()
    return st.st_size, st.st_mtime_ns

def _encode_sh(sh: np.ndarray) -> np.ndarray:

    if CACHING_METHOD == 'dc':
        return sh[:, :1, :].astype(np.float16)
    if CACHING_METHOD == 'fp32':
        return sh
    return sh.astype(np.float16)

def _restore_sh_bands(sh: np.ndarray) -> np.ndarray:

    if sh.ndim == 3 and sh.shape[1] < _SH_BANDS:
        full = np.zeros(
            (sh.shape[0], _SH_BANDS, sh.shape[2]), dtype=sh.dtype
        )
        full[:, :sh.shape[1], :] = sh
        return full
    return sh

def _cache_valid(
    npz: 'np.lib.npyio.NpzFile', ply_path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> bool:

    keys = npz.files

    if '_sh_mode' in keys and npz['_sh_mode'].item() != CACHING_METHOD:
        return False
    if '_size' in keys and '_mtime_ns' in keys:
        size, mtime_ns = _file_meta(ply_path)
        if (int(npz['_size'].item()) == size
                and int(npz['_mtime_ns'].item()) == mtime_ns):
            return True
    if '_md5' not in keys:
        return False
    return npz['_md5'].item() == _md5(ply_path, on_progress)

def get_cache_path(ply_path: Path) -> Path:
    parent = ply_path.parent
    if parent == DATA_DIR or parent == INPUT_DIR:
        return CACHE_DIR / (ply_path.stem + '.npz')
    return CACHE_DIR / parent.name / (ply_path.stem + '.npz')

def _npz_kind(npz: 'np.lib.npyio.NpzFile') -> str:

    if '_kind' in npz.files:
        return str(npz['_kind'].item())
    return _KIND_GAUSSIAN

def _open_valid_npz(
    cache_path: Path, ply_path: Path, kind: str,
    on_progress: Callable[[float], None] | None = None,
) -> 'np.lib.npyio.NpzFile | None':

    npz = np.load(str(cache_path))
    found = _npz_kind(npz)
    if found != kind:
        logger.debug(
            'Cache kind mismatch for %s: %s != %s',
            ply_path.name, found, kind,
        )
        return None
    if not _cache_valid(npz, ply_path, on_progress):
        logger.debug('Cache invalid for %s', ply_path.name)
        return None
    return npz

def load_cached(
    ply_path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> dict | None:
    cache_path = get_cache_path(ply_path)
    if not cache_path.exists():
        return None
    try:
        t0 = time.perf_counter()
        npz = _open_valid_npz(cache_path, ply_path, _KIND_GAUSSIAN,
                              on_progress)
        if npz is None:
            return None
        data = {k: npz[k] for k in _CACHE_KEYS}
        data['sh_coeffs'] = _restore_sh_bands(data['sh_coeffs'])
        logger.debug(
            'Cache HIT: %s in %.1fs',
            cache_path.name, time.perf_counter() - t0,
        )
        return data
    except Exception:
        logger.warning('Cache load failed: %s', cache_path, exc_info=True)
        return None

def save_cache(ply_path: Path, raw: dict) -> None:
    cache_path = get_cache_path(ply_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        t0 = time.perf_counter()
        size, mtime_ns = _file_meta(ply_path)
        arrays = {k: raw[k] for k in _CACHE_KEYS}

        arrays['sh_coeffs'] = _encode_sh(arrays['sh_coeffs'])
        np.savez(
            str(cache_path),
            _md5=np.array(_md5(ply_path)),
            _size=np.array(size),
            _mtime_ns=np.array(mtime_ns),
            _sh_mode=np.array(CACHING_METHOD),
            _kind=np.array(_KIND_GAUSSIAN),
            **arrays,
        )
        logger.debug(
            'Cache saved: %s in %.1fs',
            cache_path.name, time.perf_counter() - t0,
        )
    except Exception:
        logger.warning('Cache save failed: %s', cache_path, exc_info=True)

def load_cached_pointcloud(
    ply_path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> dict | None:
    cache_path = get_cache_path(ply_path)
    if not cache_path.exists():
        return None
    try:
        t0 = time.perf_counter()
        npz = _open_valid_npz(cache_path, ply_path, _KIND_POINTCLOUD,
                              on_progress)
        if npz is None:
            return None
        data = {k: np.ascontiguousarray(npz[k])
                for k in _POINTCLOUD_KEYS}
        logger.debug(
            'Point cloud cache HIT: %s in %.1fs',
            cache_path.name, time.perf_counter() - t0,
        )
        return data
    except Exception:
        logger.warning('Cache load failed: %s', cache_path, exc_info=True)
        return None

def save_cache_pointcloud(ply_path: Path, raw: dict) -> None:
    cache_path = get_cache_path(ply_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        t0 = time.perf_counter()
        size, mtime_ns = _file_meta(ply_path)
        np.savez(
            str(cache_path),
            _md5=np.array(_md5(ply_path)),
            _size=np.array(size),
            _mtime_ns=np.array(mtime_ns),
            _kind=np.array(_KIND_POINTCLOUD),
            **{k: raw[k] for k in _POINTCLOUD_KEYS},
        )
        logger.debug(
            'Point cloud cache saved: %s in %.1fs',
            cache_path.name, time.perf_counter() - t0,
        )
    except Exception:
        logger.warning('Cache save failed: %s', cache_path, exc_info=True)

def _run_tracked_save(ply_path: Path, raw: dict, kind: str) -> None:

    try:
        if kind == _KIND_POINTCLOUD:
            save_cache_pointcloud(ply_path, raw)
        else:
            save_cache(ply_path, raw)
    finally:
        with _pending_lock:
            _pending_saves.discard(threading.current_thread())

def save_cache_async(
    ply_path: Path, raw: dict, kind: str = _KIND_GAUSSIAN,
) -> None:
    t = threading.Thread(
        target=_run_tracked_save, args=(ply_path, raw, kind), daemon=True,
    )
    with _pending_lock:
        _pending_saves.add(t)
    t.start()

def flush_pending_caches(timeout: float) -> None:
    if timeout <= 0:
        return
    with _pending_lock:
        pending = list(_pending_saves)
    if not pending:
        return
    deadline = time.perf_counter() + timeout
    for t in pending:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        t.join(remaining)
    logger.debug('Flushed pending cache writes: %d threads', len(pending))
