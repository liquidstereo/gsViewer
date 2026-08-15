import logging
import time

import numpy as np

from configs.settings import PLAYBACK_FPS
from process.component.audio.fft import compute_band_levels
from process.component.audio.loader import (
    load_mono, read_audio_meta, slice_to_frame_range)
from process.component.audio.playback import AudioPlayback
from process.component.audio.settings import (
    AUDIO_DISPLAY_DB_FLOOR, AUDIO_WAVE_WINDOW_SEC, DEFAULT_BAND_NAMES,
    DEFAULT_BANDS, DEFAULT_FFT_WIN, DEFAULT_HOP,
)

logger = logging.getLogger(__name__)

_LOG_EPS = 0.000000000001

def to_display_db(levels: np.ndarray) -> np.ndarray:
    lin = np.asarray(levels, dtype=np.float32)
    floor = float(AUDIO_DISPLAY_DB_FLOOR)
    if floor >= 0.0:
        return np.clip(lin, 0.0, 1.0).astype(np.float32, copy=False)
    db = 20.0 * np.log10(np.maximum(lin, _LOG_EPS))
    out = (db - floor) / (0.0 - floor)
    out = np.clip(out, 0.0, 1.0)
    return np.where(lin > 0.0, out, 0.0).astype(np.float32, copy=False)

def _resolve_band_names(
    bands: list[tuple[float, float]] | None,
    names: list[str] | None,
    sr: int = 0,
) -> list[str]:

    if names is not None:
        return list(names)
    resolved = list(bands) if bands is not None else list(DEFAULT_BANDS)
    if sr <= 0:
        return list(DEFAULT_BAND_NAMES)
    nyq = sr / 2.0
    return [f'{hi * nyq / 1000:.1f}kHz' for _, hi in resolved]

class AudioAnalyzer:

    def __init__(
        self,
        path: str,
        win: int = DEFAULT_FFT_WIN,
        hop: int = DEFAULT_HOP,
        bands: list[tuple[float, float]] | None = None,
        band_names: list[str] | None = None,
        frame_range: str | None = None,
    ) -> None:
        t0 = time.perf_counter()
        mono, sr = load_mono(path)
        mono = slice_to_frame_range(mono, sr, frame_range, PLAYBACK_FPS)
        resolved_bands = list(bands) if bands is not None else DEFAULT_BANDS
        levels = compute_band_levels(mono, win, hop, resolved_bands)
        self._levels: np.ndarray = levels

        self._display: np.ndarray = to_display_db(levels)
        self._hop_sec: float = hop / sr
        self._bands: list[tuple[float, float]] = resolved_bands
        self.band_names: list[str] = _resolve_band_names(
            resolved_bands, band_names, sr)
        self.num_bands: int = len(resolved_bands)
        self.sample_rate: int = sr
        self.duration: float = levels.shape[0] * self._hop_sec
        self._raw: np.ndarray = mono

        self.path: str = path
        try:
            ch, file_sr, bits = read_audio_meta(path)
        except Exception:
            ch, file_sr, bits = 0, sr, 0
        self.file_channels: int = ch
        self.file_sample_rate: int = file_sr
        self.bit_depth: int = bits
        self._playback: AudioPlayback | None = None
        self._t0: float = time.perf_counter()
        logger.info(
            'AudioAnalyzer ready: %s (%.1fs, frames=%d, bands=%d) '
            'precompute %.2fs',
            path, self.duration, levels.shape[0], self.num_bands,
            time.perf_counter() - t0,
        )

    @property
    def mono(self) -> np.ndarray:
        return self._raw

    def attach_playback(self, playback: AudioPlayback) -> None:
        self._playback = playback

    def make_playback(self) -> AudioPlayback:
        pb = AudioPlayback(self._raw, self.sample_rate)
        self.attach_playback(pb)
        return pb

    def _current_index(self) -> int:
        if self.duration <= 0.0:
            return 0
        pb = self._playback
        if pb is not None:

            t = (pb.cursor / pb.sample_rate) % self.duration
        else:

            t = (time.perf_counter() - self._t0) % self.duration
        idx = int(t / self._hop_sec)
        if idx >= self._levels.shape[0]:
            return self._levels.shape[0] - 1
        return idx

    def _current_sample(self) -> int:
        n = self._raw.shape[0]
        if n <= 0 or self.duration <= 0.0:
            return 0
        pb = self._playback
        if pb is not None:

            return int(pb.cursor) % n
        t = (time.perf_counter() - self._t0) % self.duration
        return int(t * self.sample_rate) % n

    def waveform(self, width: int) -> np.ndarray:
        n = self._raw.shape[0]
        if width <= 0 or n <= 0 or self.duration <= 0.0:
            return np.zeros(max(width, 0), dtype=np.float32)
        win = max(width, int(AUDIO_WAVE_WINDOW_SEC * self.sample_rate))
        start = self._current_sample() - win // 2
        idx = np.clip(np.arange(win) + start, 0, n - 1)
        seg = self._raw[idx]

        k, m = divmod(win, width)
        counts = np.full(width, k, dtype=np.int64)
        counts[:m] += 1
        starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
        out = (np.add.reduceat(seg, starts) / counts).astype(np.float32)
        return np.clip(out, -1.0, 1.0)

    def magnitudes(self) -> np.ndarray:
        if self.duration <= 0.0:
            return np.zeros(self.num_bands, dtype=np.float32)
        return self._display[self._current_index()]

    def magnitudes_linear(self) -> np.ndarray:
        if self.duration <= 0.0:
            return np.zeros(self.num_bands, dtype=np.float32)
        return self._levels[self._current_index()]

    def magnitude_at(self, t_sec: float, band: int = 0) -> float:
        if self.duration <= 0.0 or self._hop_sec <= 0.0:
            return 0.0
        idx = int(t_sec / self._hop_sec)
        idx = max(0, min(self._levels.shape[0] - 1, idx))
        return float(self._display[idx, band])

    def magnitudes_at(self, t_sec: float) -> list[float]:
        if self.duration <= 0.0 or self._hop_sec <= 0.0:
            return [0.0] * self.num_bands
        idx = int(t_sec / self._hop_sec)
        idx = max(0, min(self._levels.shape[0] - 1, idx))
        return [float(v) for v in self._display[idx]]

    def magnitude(self, band: int | str = 0) -> float:
        if isinstance(band, str):
            idx = self.band_names.index(band)
        else:
            idx = int(band)
        if self.duration <= 0.0:
            return 0.0
        return float(self._display[self._current_index(), idx])

    @property
    def playback(self) -> AudioPlayback | None:
        return self._playback

    @property
    def bands(self) -> list[tuple[float, float]]:
        return list(self._bands)
