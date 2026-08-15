from pathlib import Path

from process.component.audio.display import display_label
from process.component.audio.settings import AUDIO_STATUS_LATENCY_SEC
from process.transform.attr_overlay import has_active_selection
from process.widget.text_case import keep_case

def _audio_status_data(window) -> dict | None:

    analyzer = getattr(window, '_audio_source', None)
    if analyzer is None:
        return None
    pb = getattr(analyzer, '_playback', None)
    sr = int(getattr(pb, 'sample_rate', 0) or 0)
    cursor = int(getattr(pb, 'cursor', 0) or 0)
    pos = cursor / sr if sr > 0 else 0.0

    lat = float(getattr(pb, 'output_latency', 0.0) or 0.0)
    pos = max(0.0, pos - lat - AUDIO_STATUS_LATENCY_SEC)
    path = getattr(analyzer, 'path', '')

    name = keep_case(Path(path).name) if path else ''
    return {
        'kind': 'audio',
        'label': display_label(window, name),
        'pos': pos,
        'duration': float(getattr(analyzer, 'duration', 0.0)),
        'brief': bool(getattr(window, '_audio_status_brief', False)),
        'sr': int(getattr(analyzer, 'file_sample_rate', 0)),
        'bits': int(getattr(analyzer, 'bit_depth', 0)),
        'channels': int(getattr(analyzer, 'file_channels', 0)),
    }

def register_audio_status(window) -> None:
    def _provider() -> dict | None:
        selected = (bool(getattr(window, '_audio_selected', False))
                    and not has_active_selection(window))
        if not selected:
            return None
        return _audio_status_data(window)

    providers = getattr(window, '_status_providers', None)
    if providers is None:
        providers = []
        window._status_providers = providers
    providers.append(_provider)
