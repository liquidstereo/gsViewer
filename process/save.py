import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import torch
from alive_progress import alive_bar
from PySide6.QtGui import QImage

from configs.settings import (
    OUTPUT_DIR, DATA_DIR,
    SAVE_EXT, SAVE_PNG_QUALITY, SAVE_JPG_QUALITY, SAVE_WITH_OVERLAY,
    SAVE_ENCODE_WORKERS, AVOID_NAME_COLLISION,
)
from process.camera import _viewmat_from_cam
from process.common.core import build_json_session_key, build_output_stem
from process.data.buffer import FrameBuffer
from process.renderer.core import render_frame
from process.record import (
    is_video_ext, create_recorder, qimage_to_rgb_bytes, FALLBACK_IMG_EXT,
)
from process.record.quality import png_quality_value

logger = logging.getLogger(__name__)

def make_save_dir(input_path: Path) -> Path:
    sub = input_path.name if input_path.is_dir() else input_path.stem
    return OUTPUT_DIR / sub

def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    ext = path.suffix
    i = 1
    while True:
        cand = parent / f'{stem}_{i:02d}{ext}'
        if not cand.exists():
            return cand
        i += 1

def resolve_save_target(
    input_path: Path, plugin_names: list[str], ext: str,
    input_ids: list[str],
) -> tuple[Path, str]:
    input_id = input_path.name if input_path.is_dir() else input_path.stem

    if not AVOID_NAME_COLLISION:
        if len([i for i in input_ids if i]) > 1:
            stem = build_output_stem(input_id, input_ids)
            if is_video_ext(ext):
                return OUTPUT_DIR, stem
            return OUTPUT_DIR / stem, stem
        if is_video_ext(ext):
            return OUTPUT_DIR, input_id
        d = make_save_dir(input_path)
        return d, d.name
    if is_video_ext(ext):
        return OUTPUT_DIR, build_json_session_key(input_ids, plugin_names)
    return OUTPUT_DIR / input_id, input_id

def save_frames(
    files: list[Path],
    buf: FrameBuffer,
    cam: dict,
    K: torch.Tensor,
    w: int,
    h: int,
    save_dir: Path,
    save_format: str | None = None,
    save_quality: str | None = None,
    stem: str | None = None,
) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    viewmat = _viewmat_from_cam(cam)
    ext = (save_format or SAVE_EXT).lower()
    base = stem or save_dir.name
    widget = _make_overlay_widget(w, h)
    if is_video_ext(ext):
        _save_video(files, buf, viewmat, K, w, h, save_dir, ext,
                    save_quality, widget, base)
    else:
        _save_images(files, buf, viewmat, K, w, h, save_dir, ext,
                     save_quality, widget, base)
    logger.info('Save complete: %d frames -> %s', len(files), save_dir)

def _make_overlay_widget(w: int, h: int):
    if not SAVE_WITH_OVERLAY:
        return None
    from process.widget.core import SplatWidget
    widget = SplatWidget(lambda *a: None)
    widget.resize(w, h)
    return widget

def _render_qimage(
    arr, widget, w: int, h: int, viewmat, i: int, total: int, name: str,
) -> QImage:
    if widget is not None:
        from process.overlay_coord import compute_gizmo_axes
        widget.set_image(arr)
        widget.set_gizmo_overlay(compute_gizmo_axes(viewmat, h, w))
        widget.set_info_overlay(f'{i+1:04d}/{total:04d}  {DATA_DIR}/{name}')
        return widget.grab().toImage()
    return QImage(
        arr.data, w, h, w * 3, QImage.Format.Format_RGB888,
    ).copy()

def _new_ssave_perf():

    return {'load': 0.0, 'render': 0.0, 'cap': 0.0, 'write': 0.0, 'n': 0}

def _ssave_log(perf) -> None:

    n = perf['n']
    if n <= 0 or n % 30 != 0:
        return
    logger.debug(
        'SSAVE_STAGE load=%.2f render=%.2f cap=%.2f write=%.2fms n=%d',
        perf['load'] / 30.0, perf['render'] / 30.0, perf['cap'] / 30.0,
        perf['write'] / 30.0, n)
    for key in ('load', 'render', 'cap', 'write'):
        perf[key] = 0.0

def _iter_rendered(files, buf, viewmat, K, w, h, widget, perf=None):
    with alive_bar(
        len(files),
        spinner=None,
        title='EXPORTING SEQUENCE...',
        title_length=23,
        length=20,
        dual_line=True,
        stats=True,
        elapsed=True,
    ) as bar:
        for i, f in enumerate(files):
            _t0 = time.perf_counter()
            splat = buf.get(i)
            _t1 = time.perf_counter()

            buf.warm(i)
            arr = render_frame(splat, viewmat, K, w, h)
            _t2 = time.perf_counter()
            img = _render_qimage(
                arr, widget, w, h, viewmat, i, len(files), f.name,
            )
            if perf is not None:
                _t3 = time.perf_counter()
                perf['load'] += (_t1 - _t0) * 1000.0
                perf['render'] += (_t2 - _t1) * 1000.0
                perf['cap'] += (_t3 - _t2) * 1000.0
            yield i, img
            bar()
        bar.title = 'OUTPUT SAVE COMPLETE'

def _write_image(img: QImage, out: Path, quality: int) -> None:

    img.save(str(out), None, quality)
    logger.info('Saved: %s', out)

def _save_images(
    files, buf, viewmat, K, w, h, save_dir, ext, quality, widget, stem,
) -> None:
    q = (
        png_quality_value(quality, SAVE_PNG_QUALITY)
        if ext == 'png' else SAVE_JPG_QUALITY
    )
    perf = _new_ssave_perf() if logger.isEnabledFor(logging.DEBUG) else None

    executor = ThreadPoolExecutor(
        max_workers=max(1, SAVE_ENCODE_WORKERS),
        thread_name_prefix='SaveEncode',
    )
    try:
        for i, img in _iter_rendered(
                files, buf, viewmat, K, w, h, widget, perf):
            out = save_dir / f'{stem}.{i:04d}.{ext}'
            _tw = time.perf_counter()
            executor.submit(_write_image, img, out, q)
            if perf is not None:
                perf['write'] += (time.perf_counter() - _tw) * 1000.0
                perf['n'] += 1
                _ssave_log(perf)
    finally:
        executor.shutdown(wait=True)

def _save_video(
    files, buf, viewmat, K, w, h, save_dir, ext, quality, widget, stem,
) -> None:
    v_stem = stem
    if AVOID_NAME_COLLISION:
        v_stem = unique_path(save_dir / f'{stem}.{ext}').stem
    rec = create_recorder(
        save_dir, v_stem, ext, w, h, quality=quality,
    )
    if rec is None:
        logger.error(
            'Recorder unavailable, fallback to %s images', FALLBACK_IMG_EXT,
        )
        _save_images(
            files, buf, viewmat, K, w, h, save_dir,
            FALLBACK_IMG_EXT, quality, widget, stem,
        )
        return
    perf = _new_ssave_perf() if logger.isEnabledFor(logging.DEBUG) else None

    executor = ThreadPoolExecutor(
        max_workers=1, thread_name_prefix='SaveVideo',
    )
    try:
        for _i, img in _iter_rendered(
                files, buf, viewmat, K, w, h, widget, perf):
            _tw = time.perf_counter()
            data = qimage_to_rgb_bytes(img)
            executor.submit(rec.write, data)
            if perf is not None:
                perf['write'] += (time.perf_counter() - _tw) * 1000.0
                perf['n'] += 1
                _ssave_log(perf)
    finally:
        executor.shutdown(wait=True)
    rec.close()
