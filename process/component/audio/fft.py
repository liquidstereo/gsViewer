import logging

import numpy as np
from numpy.lib.stride_tricks import as_strided

from process.component.audio.settings import (
    AUDIO_FFT_CHUNK_FRAMES, AUDIO_SILENCE_DBFS,
)

logger = logging.getLogger(__name__)

def _band_indices(
    rfft_len: int, bands: list[tuple[float, float]],
) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for lo, hi in bands:
        a = int(lo * rfft_len)
        b = max(a + 1, int(hi * rfft_len))
        b = min(b, rfft_len)
        out.append((a, b))
    return out

def _frame_view(
    mono: np.ndarray, n: int, win: int, hop: int,
) -> np.ndarray:

    if len(mono) < win:

        mono = np.pad(mono, (0, win - len(mono)))
    return as_strided(
        mono, shape=(n, win),
        strides=(mono.strides[0] * hop, mono.strides[0]),
    )

def _bin_weights(rfft_len: int) -> np.ndarray:

    w = np.full(rfft_len, 2.0)
    w[0] = 1.0
    w[-1] = 1.0
    return w

def _silence_floor() -> float:

    return float(10.0 ** (AUDIO_SILENCE_DBFS / 20.0))

def compute_band_levels(
    mono: np.ndarray, win: int, hop: int,
    bands: list[tuple[float, float]],
) -> np.ndarray:
    n = max(1, (len(mono) - win) // hop)
    w = np.hanning(win).astype(np.float32)
    rfft_len = win // 2 + 1
    idx_pairs = _band_indices(rfft_len, bands)

    weights = _bin_weights(rfft_len).astype(np.float32)

    denom = np.float32(float(win) * float((w.astype(np.float64) ** 2).sum()))
    levels = np.zeros((n, len(bands)), dtype=np.float32)
    frames = _frame_view(mono, n, win, hop)

    for s in range(0, n, AUDIO_FFT_CHUNK_FRAMES):
        e = min(n, s + AUDIO_FFT_CHUNK_FRAMES)
        spec = np.fft.rfft(frames[s:e] * w, axis=1)
        power = (np.abs(spec) ** 2) * weights
        for k, (a, b) in enumerate(idx_pairs):
            levels[s:e, k] = np.sqrt(power[:, a:b].sum(axis=1) / denom)
    floor = _silence_floor()
    return np.where(levels < floor, 0.0, levels).astype(
        np.float32, copy=False)
