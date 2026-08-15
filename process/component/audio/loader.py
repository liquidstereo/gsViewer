import logging
from math import gcd

import numpy as np

from process.component.audio.settings import AUDIO_TARGET_SAMPLE_RATE

logger = logging.getLogger(__name__)

_SUBTYPE_BITS: dict[str, int] = {
    'PCM_S8': 8, 'PCM_U8': 8, 'PCM_16': 16, 'PCM_24': 24,
    'PCM_32': 32, 'FLOAT': 32, 'DOUBLE': 64,
}

def read_audio_meta(path: str) -> tuple[int, int, int]:
    import soundfile as sf
    info = sf.info(path)
    bits = _SUBTYPE_BITS.get(info.subtype, 0)
    return int(info.channels), int(info.samplerate), bits

def slice_to_frame_range(
    mono: np.ndarray, sr: int, frame_range: str | None, fps: float,
) -> np.ndarray:
    if not frame_range or sr <= 0 or fps <= 0 or len(mono) == 0:
        return mono
    parts = str(frame_range).split('-')
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        return mono
    start, end = int(parts[0]), int(parts[1])
    if start < 0 or end < start:
        return mono
    spf = sr / fps
    a = max(0, min(int(round(start * spf)), len(mono)))
    b = max(a, min(int(round((end + 1) * spf)), len(mono)))
    if b <= a:
        return mono
    logger.info(
        'Audio sliced to range %d-%d: %d -> %d samples',
        start, end, len(mono), b - a)
    return mono[a:b]

def load_mono(path: str) -> tuple[np.ndarray, int]:
    import soundfile as sf
    data, sr = sf.read(path, dtype='float32', always_2d=True)
    mono = data.mean(axis=1).astype(np.float32, copy=False)
    ch = data.shape[1]
    mono, sr = _resample_to_target(mono, int(sr))
    logger.debug(
        'Audio loaded: %s (sr=%d, samples=%d, ch=%d)',
        path, sr, len(mono), ch,
    )
    return mono, sr

def _resample_to_target(
    mono: np.ndarray, src_sr: int,
) -> tuple[np.ndarray, int]:
    dst = AUDIO_TARGET_SAMPLE_RATE
    if not dst or dst == src_sr or len(mono) == 0:
        return mono, src_sr
    out = _resample(mono, src_sr, dst)
    logger.info(
        'Audio resampled: %d -> %d Hz (%d -> %d samples)',
        src_sr, dst, len(mono), len(out),
    )
    return out, dst

def _resample(mono: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    try:
        from scipy.signal import resample_poly
    except ImportError:
        return _resample_linear(mono, src_sr, dst_sr)
    g = gcd(src_sr, dst_sr)
    out = resample_poly(mono, dst_sr // g, src_sr // g)
    return out.astype(np.float32, copy=False)

def _resample_linear(
    mono: np.ndarray, src_sr: int, dst_sr: int,
) -> np.ndarray:

    n_out = int(round(len(mono) * dst_sr / src_sr))
    if n_out <= 0:
        return mono
    x_old = np.arange(len(mono), dtype=np.float64)
    x_new = np.linspace(0.0, len(mono) - 1, n_out)
    return np.interp(x_new, x_old, mono).astype(np.float32, copy=False)
