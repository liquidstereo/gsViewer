import logging
import time
from collections.abc import Callable
from pathlib import Path

from alive_progress import alive_bar

from configs.colorize import Msg
from configs.settings import PRELOAD_BAR_LEN, PRELOAD_BAR_TITLE_LEN
from process.data.loader import _numpy_to_splat, load_frame
from process.files.peek import peek_gaussian_count

logger = logging.getLogger(__name__)

_SINGLE_DECODE_W: float = 0.55

class FrameBufferPreloadMixin:

    def _fmt_label(self) -> str:
        if not self._files:
            return 'DATA'
        name = self._files[0].name.lower()
        if name.endswith('.compressed.ply'):
            return 'CPLY'
        return self._files[0].suffix.lstrip('.').upper() or 'DATA'

    def _cache_eligible(self) -> bool:
        if not self._files:
            return False
        name = self._files[0].name.lower()
        return (
            name.endswith('.compressed.ply')
            or self._files[0].suffix.lower() in ('.ply', '.sog')
        )

    def _cache_exists(self) -> bool:
        if not self._files:
            return False
        from process.data.cache import get_cache_path
        return get_cache_path(self._files[0]).exists()

    def _preload_title(self) -> str:
        fmt = self._fmt_label()
        if not self._use_cache or not self._cache_eligible():
            return f'LOADING {fmt} FILES...'
        if self._cache_exists():
            return f'LOADING {fmt} CACHE...'
        return f'BUILDING {fmt} CACHE...'

    def preload_all(
        self, on_progress: Callable[[], None]
    ) -> None:
        from concurrent.futures import as_completed
        futures = {
            self._executor.submit(
                load_frame, f, self._use_cache
            ): i
            for i, f in enumerate(self._files)
        }
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                raw = fut.result()
                with self._lock:
                    self._ram_cache[idx] = raw
                logger.debug('RAM loaded frame %d', idx)
            except Exception:
                logger.error(
                    'Failed to load frame %d', idx, exc_info=True
                )
            on_progress()

    def preload_with_progress(self) -> None:
        if len(self._files) == 1:
            self._preload_single_large(self._files[0])
            return
        n = len(self._files)
        count = [0]
        t0 = time.perf_counter()
        with alive_bar(
            n,
            spinner=None,
            title=self._preload_title(),
            title_length=PRELOAD_BAR_TITLE_LEN,
            length=PRELOAD_BAR_LEN,
            dual_line=True,
            stats=True,
            elapsed=True,
            manual=False,
            enrich_print=False,
        ) as bar:
            def _on_prog_multi() -> None:
                bar()
                count[0] += 1
                if count[0] >= n:
                    bar.title = 'LOADING... PLEASE WAIT...'
            self.preload_all(_on_prog_multi)
            bar.title = 'FILES LOAD COMPLETE'
        logger.info(
            'RAM preload complete: %d files in %.1fs',
            n, time.perf_counter() - t0,
        )

    def _preload_single_large(self, path: Path) -> None:
        t0 = time.perf_counter()
        n_total = peek_gaussian_count(path)

        title = self._preload_title()
        with alive_bar(
            manual=True,
            spinner=None,
            title=title,
            title_length=PRELOAD_BAR_TITLE_LEN,
            length=PRELOAD_BAR_LEN,
            dual_line=True,
            stats=False,
            elapsed=True,
            enrich_print=False,
        ) as bar:
            def _set(frac: float) -> None:
                if n_total > 0:
                    loaded = int(frac * n_total)
                    bar.text = Msg.Dim(
                        f'GAUSSIAN POINTS LOADED: {loaded}/{n_total}',
                        verbose=True,
                    )
                bar(frac)

            def _on_decode(frac: float) -> None:
                _set(frac * _SINGLE_DECODE_W)

            def _on_upload(frac: float) -> None:
                _set(_SINGLE_DECODE_W + frac * (1.0 - _SINGLE_DECODE_W))

            raw = load_frame(
                path, self._use_cache, on_progress=_on_decode
            )
            splat = _numpy_to_splat(raw, on_progress=_on_upload)
            _set(1.0)
            bar.title = 'GAUSSIAN POINTS LOADED'
        with self._lock:
            self._ram_cache[0] = raw
            self._gpu_cache[0] = splat
        logger.info(
            'Single file preload complete: %s in %.1fs',
            path.name, time.perf_counter() - t0,
        )

    def preload_gpu_sync(self) -> None:
        n = len(self._files)
        is_single = n == 1
        n_load = min(n, self._gpu_ahead + 1)
        t0 = time.perf_counter()
        with alive_bar(
            None if is_single else n_load,
            spinner=None,
            title='GPU CACHE BUILDING...',
            title_length=PRELOAD_BAR_TITLE_LEN,
            length=PRELOAD_BAR_LEN,
            dual_line=True,
            manual=is_single,
            stats=not is_single,
            elapsed=True,
            enrich_print=False,
        ) as bar:
            for i in range(n_load):
                with self._lock:
                    already = i in self._gpu_cache
                    raw = self._ram_cache.get(i)
                    cam_pos = self._init_cam_pos
                if not already and raw is not None:
                    splat = _numpy_to_splat(raw, cam_pos)
                    with self._lock:
                        self._gpu_cache[i] = splat
                    logger.debug('GPU preloaded frame %d', i)
                bar(1.0) if is_single else bar()
            bar.title = 'GPU CACHE READY'
        logger.info(
            'GPU sync preload complete: %d/%d frames in %.1fs',
            n_load, n, time.perf_counter() - t0,
        )

    def preload_external(
        self, on_each_done: Callable[[], None],
    ) -> None:
        if len(self._files) == 0:
            return
        t0 = time.perf_counter()
        self.preload_all(on_each_done)
        logger.info(
            'RAM preload (silent) complete: %d files in %.1fs',
            len(self._files), time.perf_counter() - t0,
        )
