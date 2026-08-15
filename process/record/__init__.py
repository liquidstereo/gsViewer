import logging
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage

from process.record.settings import (
    VIDEO_EXTS, FALLBACK_IMG_EXT, DEFAULT_SAVE_FPS,
)
from process.record.probe import ffmpeg_available, select_codec
from process.record.recorder import FFmpegRecorder
from process.record.quality import video_codec_override

logger = logging.getLogger(__name__)

__all__ = [
    'is_video_ext', 'create_recorder', 'qimage_to_rgb_bytes',
    'FFmpegRecorder', 'VIDEO_EXTS', 'FALLBACK_IMG_EXT',
]

def is_video_ext(ext: str) -> bool:
    return ext.lower() in VIDEO_EXTS

def create_recorder(
    out_dir: Path, stem: str, ext: str, w: int, h: int,
    fps: int = DEFAULT_SAVE_FPS, quality: str | None = None,
) -> FFmpegRecorder | None:
    if not ffmpeg_available():
        logger.error('ffmpeg not found, fallback to image save')
        return None
    out = out_dir / f'{stem}.{ext}'
    codec, args_override = video_codec_override(quality)
    if codec is None:
        codec = select_codec()
    rec = FFmpegRecorder(out, w, h, fps, codec, args_override=args_override)
    if not rec.start():
        return None
    return rec

def qimage_to_rgb_bytes(img: QImage) -> bytes:
    img = img.convertToFormat(QImage.Format.Format_RGB888)
    w = img.width()
    h = img.height()
    bpl = img.bytesPerLine()
    buf = np.frombuffer(img.constBits(), dtype=np.uint8).reshape(h, bpl)
    return np.ascontiguousarray(buf[:, : w * 3]).tobytes()
