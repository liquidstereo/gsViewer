from process.component.audio.analyzer import AudioAnalyzer
from process.component.audio.path import (
    auto_detect_audio_path, primary_audio_path, resolve_audio_path,
)
from process.component.audio.playback import AudioPlayback
from process.component.audio.plugin import AudioAnalyzerPlugin
from process.component.audio.settings import (
    AUDIO_DIR, AUDIO_OVERLAY_MODE, DEFAULT_BAND_NAMES, DEFAULT_BANDS,
    DEFAULT_FFT_WIN, DEFAULT_HOP,
)

PLUGIN_NAME: str = 'audio'
REQUIRES: list[str] = []
REQUIRES_PLUGINS: list[str] = []

def _resolve_audio_csv(raw: str | None) -> list[str]:

    if not raw:
        return []
    items = [s.strip() for s in raw.split(',') if s.strip()]
    return [r for r in (resolve_audio_path(it) for it in items) if r]

def create_plugin(
    audio: str | list[str] | None = None,
    frame_range: str | None = None, **kwargs
) -> AudioAnalyzerPlugin:
    if isinstance(audio, list):
        return AudioAnalyzerPlugin(audio or None, frame_range=frame_range)
    return AudioAnalyzerPlugin(
        _resolve_audio_csv(audio) or None, frame_range=frame_range)

__all__ = [
    'AUDIO_DIR', 'AUDIO_OVERLAY_MODE', 'AudioAnalyzer',
    'AudioAnalyzerPlugin', 'AudioPlayback',
    'DEFAULT_BAND_NAMES', 'DEFAULT_BANDS', 'DEFAULT_FFT_WIN',
    'DEFAULT_HOP', 'PLUGIN_NAME', 'REQUIRES',
    'REQUIRES_PLUGINS', 'auto_detect_audio_path', 'create_plugin',
    'primary_audio_path', 'resolve_audio_path',
]
