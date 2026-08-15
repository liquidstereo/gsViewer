import logging
import time
from pathlib import Path

import numpy as np
import torch
from alive_progress import alive_bar

from configs.colorize import Msg
from configs.settings import PRELOAD_BAR_LEN, PRELOAD_BAR_TITLE_LEN
from process.data.cache import get_cache_path
from process.data.pointcloud import load_point_cloud
from process.files.peek import peek_gaussian_count

logger = logging.getLogger(__name__)

POINTCLOUD_SPLAT_KEY: str = 'pointcloud'
DEVICE_CACHE_KEY: str = '_device_tensors'

def with_device_means(splat: dict) -> dict:
    cache = splat.get(DEVICE_CACHE_KEY)
    if cache is None:
        if not torch.cuda.is_available():
            return splat
        device = torch.device('cuda')
        cache = {
            'means': splat['means'].to(device),
            'opacities': splat['opacities'].to(device),
        }
        splat[DEVICE_CACHE_KEY] = cache
        logger.debug('Point cloud tensors staged on %s (%d points)',
                     device, splat.get('count', 0))
    out = dict(splat)
    out.update(cache)
    return out

def is_pointcloud_splat(splat: dict | None) -> bool:
    return bool(splat) and bool(splat.get(POINTCLOUD_SPLAT_KEY))

def build_pointcloud_splat(data: dict) -> dict:
    means_np = np.ascontiguousarray(data['means_np'])
    colors_np = np.ascontiguousarray(data['colors_np'])
    count = int(means_np.shape[0])
    return {
        'means': torch.from_numpy(means_np),
        'colors': torch.from_numpy(colors_np),
        'means_np': means_np,
        'colors_np': colors_np,

        'opacities': torch.ones(count, dtype=torch.float32),
        'count': count,
        POINTCLOUD_SPLAT_KEY: True,
    }

class PointCloudBuffer:

    def __init__(self, files: list, use_cache: bool = True) -> None:
        self._files = [Path(f) for f in files]
        self._use_cache = use_cache
        self._splat: dict | None = None

    def _preload_title(self) -> str:

        if not self._use_cache:
            return 'LOADING POINT CLOUD FILES...'
        if get_cache_path(self._files[0]).exists():
            return 'LOADING POINT CLOUD CACHE...'
        return 'BUILDING POINTS CACHE...'

    def _ensure(self, on_progress=None) -> dict:
        if self._splat is None:
            path = self._files[0]
            data = load_point_cloud(
                path, use_cache=self._use_cache, on_progress=on_progress,
            )
            self._splat = build_pointcloud_splat(data)
            logger.info(
                'Point cloud loaded: %s (%d points, GL_POINTS path)',
                path.name, self._splat['count'],
            )
        return self._splat

    def get(self, idx: int) -> dict:
        return self._ensure()

    def preload_with_progress(self) -> None:
        if self._splat is not None:
            return
        t0 = time.perf_counter()
        path = self._files[0]
        n_total = peek_gaussian_count(path)
        with alive_bar(
            manual=True,
            spinner=None,
            title=self._preload_title(),
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
                        f'POINTS LOADED: {loaded}/{n_total}',
                        verbose=True,
                    )
                bar(frac)

            self._ensure(on_progress=_set)
            _set(1.0)
            bar.title = 'POINT CLOUD DATA LOADED'
        logger.info(
            'Point cloud preload complete: %s in %.1fs',
            path.name, time.perf_counter() - t0,
        )

    def preload_gpu_sync(self) -> None:
        return None

    def set_cam_pos(self, cam_pos: torch.Tensor) -> None:
        return None

    def warm(self, idx: int) -> None:
        return None

    def set_gpu_ahead(self, n: int) -> None:
        return None

    def release_gpu(self) -> None:
        return None

    def is_gpu_resident(self, idx: int) -> bool:
        return True

    def gpu_resident_count(self) -> int:
        return 0

    def shutdown(self) -> None:
        self._splat = None
