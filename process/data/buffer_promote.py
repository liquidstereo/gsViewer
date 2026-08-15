import logging

import torch

from process.data.loader import _numpy_to_splat, build_cpu_splat
from process.data.ram_cache import upload_to_gpu

logger = logging.getLogger(__name__)

def _finalize_gpu_splat(splat: dict, cam_pos) -> dict:
    splat['quats'] = torch.nn.functional.normalize(
        splat['quats'], p=2, dim=-1
    )
    splat['opacities'] = torch.sigmoid(splat['opacities'])
    splat['sh_coeffs'] = splat['sh_coeffs'].float()
    if cam_pos is not None:
        from process.renderer.core import compute_colors
        splat['colors'] = compute_colors(splat, cam_pos)
    return splat

def _upload_finalize(cpu: dict, cam_pos) -> dict:
    return _finalize_gpu_splat(upload_to_gpu(cpu), cam_pos)

class FrameBufferPromoteMixin:

    def _on_promoted(self, idx: int, future) -> None:
        try:
            splat = future.result()
            with self._lock:
                self._gpu_cache[idx] = splat
                self._gpu_pending.discard(idx)
            logger.debug('GPU promoted frame %d', idx)
        except Exception:
            with self._lock:
                self._gpu_pending.discard(idx)
            logger.error(
                'Failed to promote frame %d', idx, exc_info=True
            )

    def _on_cpu_built(self, idx: int, future) -> None:
        try:
            cpu = future.result()
            with self._lock:
                self._cpu_cache[idx] = cpu
                self._cpu_pending.discard(idx)
            logger.debug('CPU cached frame %d', idx)
        except Exception:
            with self._lock:
                self._cpu_pending.discard(idx)
            logger.error(
                'Failed to cache frame %d', idx, exc_info=True
            )

    def _promote_gpu(self, gpu_want: set, cam_pos) -> None:
        with self._lock:
            todo = [
                k for k in gpu_want
                if k not in self._gpu_cache
                and k not in self._gpu_pending
                and (k in self._cpu_cache or k in self._ram_cache)
            ]
            self._gpu_pending.update(todo)
            src = {
                k: (self._cpu_cache.get(k), self._ram_cache.get(k))
                for k in todo
            }
        for k in todo:
            cpu, raw = src[k]
            if cpu is not None:
                fut = self._executor.submit(_upload_finalize, cpu, cam_pos)
            else:
                fut = self._executor.submit(_numpy_to_splat, raw, cam_pos)
            fut.add_done_callback(
                lambda f, i=k: self._on_promoted(i, f)
            )

    def _promote_cpu(self, cpu_keep: list) -> None:
        with self._lock:
            todo = [
                k for k in cpu_keep
                if k not in self._cpu_cache
                and k not in self._cpu_pending
                and k in self._ram_cache
            ]
            self._cpu_pending.update(todo)
            raws = {k: self._ram_cache[k] for k in todo}
        for k in todo:
            fut = self._executor.submit(build_cpu_splat, raws[k])
            fut.add_done_callback(
                lambda f, i=k: self._on_cpu_built(i, f)
            )
