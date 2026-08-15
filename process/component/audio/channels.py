import logging
from pathlib import Path

from process.common.natural_sort import natural_sorted
from process.component.audio.analyzer import AudioAnalyzer
from process.component.audio.settings import (
    AUDIO_AUTO_EXTS, AUDIO_MAX_PRELOAD_CHANNELS, DEFAULT_FFT_WIN, DEFAULT_HOP,
)

logger = logging.getLogger(__name__)

def resolve_channels(path: str | Path) -> list[Path]:
    p = Path(path)
    if not p.is_dir():
        return []
    return [q for q in natural_sorted(p.iterdir())
            if q.is_file() and q.suffix.lower() in AUDIO_AUTO_EXTS]

def _channel_names(files: list[Path]) -> list[str]:
    stems = [f.stem for f in files]
    if len(set(stems)) == len(stems):
        return stems

    return [f.name for f in files]

class AudioChannelSet:

    def __init__(
        self,
        files: list[Path],
        frame_range: str | None = None,
        win: int = DEFAULT_FFT_WIN,
        hop: int = DEFAULT_HOP,
    ) -> None:
        self._files: list[Path] = list(files)
        self._names: list[str] = _channel_names(self._files)
        self._frame_range: str | None = frame_range
        self._win: int = win
        self._hop: int = hop
        self._cache: dict[str, AudioAnalyzer] = {}
        self._current: str = self._names[0] if self._names else ''

    @property
    def names(self) -> list[str]:
        return list(self._names)

    @property
    def current(self) -> str:
        return self._current

    def path_of(self, name: str) -> Path | None:
        if name not in self._names:
            return None
        return self._files[self._names.index(name)]

    def analyzer(self, name: str) -> AudioAnalyzer | None:
        if name in self._cache:
            return self._cache[name]
        path = self.path_of(name)
        if path is None:
            return None
        try:
            an = AudioAnalyzer(
                str(path), self._win, self._hop,
                frame_range=self._frame_range)
        except Exception as e:
            logger.error('Audio channel load failed: %s (%s)', path.name, e)
            return None
        self._cache[name] = an
        return an

    def set_current(self, name: str) -> bool:
        if name not in self._names:
            return False
        self._current = name
        return True

    def preload(self, limit: int = AUDIO_MAX_PRELOAD_CHANNELS) -> int:
        for name in self._names[:max(0, limit)]:
            self.analyzer(name)
        skipped = max(0, len(self._names) - max(0, limit))
        if skipped:
            logger.info(
                'Audio channels: %d preloaded, %d on-demand (limit %d)',
                len(self._cache), skipped, limit,
            )
        return len(self._cache)

def make_single_source(
    path: str, frame_range: str | None = None,
    win: int = DEFAULT_FFT_WIN, hop: int = DEFAULT_HOP,
) -> tuple:
    analyzer = AudioAnalyzer(str(path), win, hop, frame_range=frame_range)
    return analyzer, analyzer.make_playback()

def init_channel_source(
    window, path: str | None, frame_range: str | None = None,
    win: int = DEFAULT_FFT_WIN, hop: int = DEFAULT_HOP,
) -> tuple | None:
    files = resolve_channels(path) if path else []
    if not files:
        return None
    channels = AudioChannelSet(files, frame_range, win, hop)
    channels.preload()
    analyzer = channels.analyzer(channels.current)
    if analyzer is None:
        logger.error('Audio channels found but none decodable: %s', path)
        return None
    window._audio_channels = channels
    logger.info(
        'Audio channels ready: %d (%s), current=%s',
        len(channels.names), ', '.join(channels.names), channels.current,
    )
    return analyzer, analyzer.make_playback()

def register_audio_source_listener(window, listener) -> None:
    listeners = getattr(window, '_audio_source_listeners', None)
    if listeners is None:
        listeners = []
        window._audio_source_listeners = listeners
    if listener not in listeners:
        listeners.append(listener)

def notify_audio_source_changed(window, analyzer) -> None:
    for listener in list(getattr(window, '_audio_source_listeners', None)
                         or []):
        try:
            listener(window, analyzer)
        except Exception as e:
            logger.error('Audio source listener failed: %s', e)

def select_channel(window, name: str) -> bool:
    channels = getattr(window, '_audio_channels', None)
    if channels is None or name not in channels.names:
        return False
    if name == channels.current and getattr(window, '_audio_source', None):
        return True
    analyzer = channels.analyzer(name)
    if analyzer is None:
        return False
    playback = getattr(window, '_audio_playback', None)
    if playback is not None:
        if not playback.swap_source(analyzer.mono):
            return False
        analyzer.attach_playback(playback)
    window._audio_source = analyzer
    channels.set_current(name)

    notify_audio_source_changed(window, analyzer)
    logger.info('Audio channel selected: %s', name)
    return True
