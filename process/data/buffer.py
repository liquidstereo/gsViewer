import gc
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import torch

from configs.settings import (
    GPU_AHEAD, GPU_DEFRAG_THRESHOLD_MB, JITTER_GPU_AHEAD, PRELOAD_WORKERS,
)
from process.data.buffer_preload import FrameBufferPreloadMixin
from process.data.buffer_promote import (
    FrameBufferPromoteMixin, _upload_finalize,
)
from process.data.loader import (
    _numpy_to_splat, build_cpu_splat, load_frame,
)
from process.data.ram_cache import (
    auto_cpu_budget_frames, centered_window, forward_window,
    nearest_first, splat_nbytes,
)

logger = logging.getLogger(__name__)

class FrameBuffer(FrameBufferPreloadMixin, FrameBufferPromoteMixin):
    def __init__(
        self,
        files: list[Path],
        gpu_ahead: int = GPU_AHEAD,
        workers: int = PRELOAD_WORKERS,
        use_cache: bool = True,
    ) -> None:
        self._files = files
        self._gpu_ahead = gpu_ahead
        self._use_cache = use_cache

        self._window_radius = 0

        self._gpu_explicit: set[int] | None = None
        self._ram_cache: dict[int, dict] = {}
        self._gpu_cache: dict[int, dict] = {}
        self._gpu_pending: set[int] = set()

        self._cpu_cache: dict[int, dict] = {}
        self._cpu_pending: set[int] = set()
        self._cpu_budget = 0

        self._defrag_threshold = GPU_DEFRAG_THRESHOLD_MB * 1024 * 1024
        self._init_cam_pos: torch.Tensor | None = None
        self._lock = threading.Lock()
        self._trigger = threading.Event()
        self._head = 0
        self._executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix='FrameLoader',
        )
        threading.Thread(
            target=self._run, daemon=True, name='BufferManager'
        ).start()
        logger.info(
            'FrameBuffer init: %d files, gpu_ahead=%d',
            len(files), gpu_ahead,
        )

    def set_cam_pos(self, cam_pos: torch.Tensor) -> None:
        from process.renderer.core import compute_colors
        with self._lock:
            self._init_cam_pos = cam_pos
            for splat in self._gpu_cache.values():
                splat['colors'] = compute_colors(splat, cam_pos)

        logger.info(
            'Colors precomputed for %d GPU frames',
            len(self._gpu_cache),
        )

    @property
    def gpu_resident_count(self) -> int:
        return len(self._gpu_cache)

    def is_gpu_resident(self, idx: int) -> bool:
        with self._lock:
            return idx in self._gpu_cache

    def warm(self, idx: int) -> None:
        with self._lock:
            self._head = idx
        self._trigger.set()

    def set_window_radius(self, radius: int) -> None:
        r = max(0, int(radius))
        with self._lock:
            if self._window_radius == r:
                return
            self._window_radius = r
        self._trigger.set()

    def set_gpu_want(self, frames: list | None) -> None:
        want = None if frames is None else {int(i) for i in frames}
        with self._lock:
            if self._gpu_explicit == want:
                return
            self._gpu_explicit = want
        self._trigger.set()

    def set_gpu_ahead(self, n: int) -> None:
        v = max(0, int(n))
        with self._lock:
            if self._gpu_ahead == v:
                return
            self._gpu_ahead = v
        self._trigger.set()

    def release_gpu(self) -> None:
        with self._lock:
            self._gpu_cache.clear()
            self._gpu_pending.clear()
        torch.cuda.empty_cache()

    def invalidate_slice(self) -> None:
        with self._lock:
            self._gpu_cache.clear()
            self._gpu_pending.clear()
            self._cpu_cache.clear()
            self._cpu_pending.clear()
        torch.cuda.empty_cache()
        logger.info('Slice invalidated: GPU/CPU caches cleared')

    def prewarm_window(self) -> list[int]:
        n = len(self._files)
        with self._lock:
            head = self._head
            radius = self._window_radius
        if radius <= 0 or n <= 1:
            return []
        return nearest_first(centered_window(head, n, radius), head, n)

    def prewarm_frame(self, idx: int) -> tuple[float, float]:
        with self._lock:
            if idx in self._gpu_cache or idx in self._cpu_cache:
                return 0.0, 0.0
            raw = self._ram_cache.get(idx)
        load_ms = 0.0
        if raw is None:
            t0 = time.perf_counter()
            raw = load_frame(self._files[idx], self._use_cache)
            load_ms = (time.perf_counter() - t0) * 1000.0
            with self._lock:
                self._ram_cache[idx] = raw
        t1 = time.perf_counter()
        cpu = build_cpu_splat(raw)
        build_ms = (time.perf_counter() - t1) * 1000.0
        with self._lock:
            self._cpu_cache[idx] = cpu
        return load_ms, build_ms

    def get(self, idx: int) -> dict:
        with self._lock:
            if idx in self._gpu_cache:
                logger.debug('GPU HIT frame %d', idx)
                return self._gpu_cache[idx]
            cpu = self._cpu_cache.get(idx)
            cam_pos = self._init_cam_pos
        if cpu is not None:
            logger.debug('CPU HIT frame %d -- uploading', idx)
            splat = _upload_finalize(cpu, cam_pos)
            with self._lock:
                self._gpu_cache[idx] = splat
            return splat
        logger.debug('GPU MISS frame %d -- promoting from RAM', idx)
        with self._lock:
            raw = self._ram_cache.get(idx)
        if raw is None:
            logger.warning(
                'RAM MISS frame %d -- loading from disk', idx
            )
            raw = load_frame(self._files[idx], self._use_cache)
            with self._lock:
                self._ram_cache[idx] = raw
        splat = _numpy_to_splat(raw, cam_pos)
        with self._lock:
            self._gpu_cache[idx] = splat
        return splat

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        with self._lock:
            self._gpu_cache.clear()
            self._ram_cache.clear()
            self._gpu_pending.clear()
            self._cpu_cache.clear()
            self._cpu_pending.clear()
        torch.cuda.empty_cache()
        gc.collect()
        logger.info('FrameBuffer shutdown: caches cleared')

    def _run(self) -> None:
        n = len(self._files)
        while True:
            self._trigger.wait()
            self._trigger.clear()
            with self._lock:
                head = self._head
                cam_pos = self._init_cam_pos
                radius = self._window_radius
                explicit = (None if self._gpu_explicit is None
                            else set(self._gpu_explicit))
            self._ensure_budget(n)
            gpu_want = (explicit if explicit is not None
                        else self._gpu_window(head, n, radius))
            cpu_keep = self._cpu_keep(head, n, radius)
            self._evict(gpu_want, cpu_keep)
            self._maybe_defrag()
            self._promote_cpu(cpu_keep)
            self._promote_gpu(gpu_want, cam_pos)

    def _maybe_defrag(self) -> None:

        if self._defrag_threshold <= 0:
            return
        resv = torch.cuda.memory_reserved()
        alloc = torch.cuda.memory_allocated()
        if resv - alloc <= self._defrag_threshold:
            return
        torch.cuda.empty_cache()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                'Defrag empty_cache: reserved %.0fMB alloc %.0fMB',
                resv / 1048576.0, alloc / 1048576.0,
            )

    def _gpu_window(self, head: int, n: int, radius: int) -> set:
        if radius <= 0:
            return forward_window(head, n, self._gpu_ahead + 1)

        return centered_window(head, n, min(radius, JITTER_GPU_AHEAD))

    def _cpu_keep(self, head: int, n: int, radius: int) -> list:
        if radius <= 0 or self._cpu_budget <= 0:
            return []
        if radius >= n and self._cpu_budget < n:

            return list(range(self._cpu_budget))
        want = centered_window(head, n, radius)
        return nearest_first(want, head, n)[:self._cpu_budget]

    def _ensure_budget(self, n: int) -> None:
        if self._cpu_budget > 0:
            return
        with self._lock:
            sample = next(iter(self._gpu_cache.values()), None)
        if sample is None:
            return
        nb = splat_nbytes(sample)
        self._cpu_budget = min(n, auto_cpu_budget_frames(nb))
        logger.info(
            'CPU splat cache budget: %d frames (%d MB/frame)',
            self._cpu_budget, nb // (1024 * 1024),
        )

    def _evict(self, gpu_want: set, cpu_keep: list) -> None:
        keep = set(cpu_keep)
        with self._lock:
            for k in [k for k in self._gpu_cache if k not in gpu_want]:
                del self._gpu_cache[k]
            for k in [k for k in self._cpu_cache if k not in keep]:
                del self._cpu_cache[k]
