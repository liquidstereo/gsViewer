from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from configs.settings_attr import ATTR_PANEL_PAD
from configs.settings_overlay import (
    WAVEFORM_OVERLAY_ALPHA, WAVEFORM_OVERLAY_COLOR, WAVEFORM_OVERLAY_GAIN,
    WAVEFORM_OVERLAY_LINE_W, WAVEFORM_STACK_GAP,
)
from process.component.audio.overlay import (
    draw_waveform_polyline, paint_wave_border,
)
from process.component.audio.settings import (
    AUDIO_OVERLAY_BOX_ROWS, AUDIO_OVERLAY_PAD_RATIO, AUDIO_WAVE_AMP_RATIO,
)
from process.widget.overlays.mini_panel import (
    mini_panel_height, paint_mini_panel,
)
from process.widget.scale import (
    scaled_margin, scaled_seq_inset_margin, scaled_seq_inset_w,
    scaled_waveform_inset_margin, scaled_waveform_inset_w,
)

def _seq_inset_height(seq_frame, w: int) -> int:
    if seq_frame is None:
        return 0
    fh, fw = seq_frame.shape[:2]
    if fw <= 0:
        return 0
    return max(1, round(scaled_seq_inset_w(w) * fh / fw))

def _title_text(source) -> str:
    raw = getattr(source, 'path', None)
    stem = Path(raw).stem if raw else ''
    return f'audio: {stem}' if stem else 'audio'

def _panel_bottom(seq_frame, w: int, h: int, margin: int) -> float:
    seq_h = _seq_inset_height(seq_frame, w)
    if seq_h > 0:
        gap = scaled_margin(w, WAVEFORM_STACK_GAP)
        return h - scaled_seq_inset_margin(w) - seq_h - gap
    return h - margin

def paint_waveform_overlay(
    painter: QPainter, source, seq_frame, w: int, h: int,
) -> None:
    if source is None or WAVEFORM_OVERLAY_ALPHA <= 0.0:
        return
    panel_w = scaled_waveform_inset_w(w)
    margin = scaled_waveform_inset_margin(w)
    pad = scaled_margin(w, ATTR_PANEL_PAD)
    samples = source.waveform(max(int(panel_w - pad * 2), 2))
    if samples is None or len(samples) <= 1:
        return
    panel_h = mini_panel_height(w, AUDIO_OVERLAY_BOX_ROWS)
    x0 = w - panel_w - margin
    y0 = _panel_bottom(seq_frame, w, h, margin) - panel_h

    def _content(p: QPainter, box_rect: QRectF) -> None:
        paint_wave_border(p, box_rect)
        draw_waveform_polyline(
            p, box_rect, samples, WAVEFORM_OVERLAY_COLOR,
            WAVEFORM_OVERLAY_LINE_W, WAVEFORM_OVERLAY_GAIN,
            AUDIO_WAVE_AMP_RATIO, AUDIO_OVERLAY_PAD_RATIO,
        )

    paint_mini_panel(
        painter, w, x0, y0, panel_w, _title_text(source),
        AUDIO_OVERLAY_BOX_ROWS, _content, alpha=WAVEFORM_OVERLAY_ALPHA,
    )
