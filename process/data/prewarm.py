import logging
import time

from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

def run_prewarm(window, targets: list, label: str) -> dict:
    total = len(targets)
    widget = getattr(window, '_widget', None)
    window._buffering = True
    resume_audio = getattr(window, '_playing', False)
    if resume_audio:
        _pause_hooks(window, True)
    t0 = time.perf_counter()
    load_ms = 0.0
    build_ms = 0.0
    loaded = 0
    built = 0
    try:
        for done, (buf, idx) in enumerate(targets, start=1):
            lm, bm = buf.prewarm_frame(idx)
            load_ms += lm
            build_ms += bm
            loaded += 1 if lm > 0.0 else 0
            built += 1 if bm > 0.0 else 0
            if widget is not None:
                pct = int(done / total * 100) if total else 100
                widget.set_loading_overlay(f'{label}...({pct}%)')
                widget.update()
            QApplication.processEvents()
    finally:
        window._buffering = False
        if resume_audio:
            window._reset_playback_clock()
            _pause_hooks(window, False)
        if widget is not None:
            widget.set_loading_overlay(None)
        window._render_current()
    elapsed = (time.perf_counter() - t0) * 1000.0
    return {
        'total': total, 'elapsed_ms': elapsed, 'load_ms': load_ms,
        'build_ms': build_ms, 'loaded': loaded, 'built': built,
    }

def _pause_hooks(window, paused: bool) -> None:
    for hook in getattr(window, '_pause_hooks', []):
        try:
            hook(paused)
        except Exception:
            logger.exception('Prewarm pause hook error (paused=%s)', paused)
