import logging

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from configs.settings_attr import (
    ATTR_PANEL_FILL_COLOR, ATTR_PANEL_TRACK_COLOR,
)
from process.component.audio.settings import (
    AUDIO_OVERLAY_BAR_GAP_RATIO, AUDIO_OVERLAY_MODE, AUDIO_OVERLAY_PAD_RATIO,
    AUDIO_WAVE_AMP_RATIO, AUDIO_WAVE_LINE_W, WAVEFORM_GAIN,
)

logger = logging.getLogger(__name__)

def make_equalizer_paint(window):
    def _paint(painter: QPainter, rect: QRectF) -> None:
        paint_wave_border(painter, rect)
        source = getattr(window, '_audio_source', None)
        if source is None:
            return
        if AUDIO_OVERLAY_MODE == 'waveform':
            _paint_waveform(painter, rect, source)
            return

        _paint_bars(painter, rect, source.magnitudes())

    return _paint

def paint_wave_border(painter: QPainter, rect: QRectF) -> None:
    painter.save()
    painter.setPen(QColor(ATTR_PANEL_TRACK_COLOR))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(rect)
    painter.restore()

def draw_waveform_polyline(
    painter: QPainter, rect: QRectF, samples: np.ndarray, color: str,
    line_w: float, gain: float, amp_ratio: float, pad_ratio: float,
) -> None:
    pad = rect.height() * pad_ratio
    inner = rect.adjusted(pad, pad, -pad, -pad)
    n = len(samples)
    if n <= 1:
        return
    mid = inner.center().y()
    amp = inner.height() * 0.5 * amp_ratio
    step = inner.width() / (n - 1)
    poly = QPolygonF()
    for i in range(n):
        x = inner.left() + i * step
        v = float(samples[i]) * gain
        v = -1.0 if v < -1.0 else (1.0 if v > 1.0 else v)
        y = mid - v * amp
        poly.append(QPointF(x, y))
    painter.save()
    pen = QPen(QColor(color))
    pen.setWidthF(line_w)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPolyline(poly)
    painter.restore()

def _paint_waveform(painter: QPainter, rect: QRectF, source) -> None:
    pad = rect.height() * AUDIO_OVERLAY_PAD_RATIO
    inner = rect.adjusted(pad, pad, -pad, -pad)
    width = max(int(inner.width()), 2)
    samples = source.waveform(width)
    draw_waveform_polyline(
        painter, rect, samples, ATTR_PANEL_FILL_COLOR, AUDIO_WAVE_LINE_W,
        WAVEFORM_GAIN, AUDIO_WAVE_AMP_RATIO, AUDIO_OVERLAY_PAD_RATIO,
    )

def _paint_bars(painter: QPainter, rect: QRectF, mags) -> None:
    n = len(mags)
    if n <= 0:
        return
    pad = rect.height() * AUDIO_OVERLAY_PAD_RATIO
    inner = rect.adjusted(pad, pad, -pad, -pad)
    gap_ratio = AUDIO_OVERLAY_BAR_GAP_RATIO
    bar_w = inner.width() / (n + (n - 1) * gap_ratio)
    gap = bar_w * gap_ratio
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(ATTR_PANEL_FILL_COLOR))
    for i in range(n):
        m = float(mags[i])
        m = 0.0 if m < 0.0 else (1.0 if m > 1.0 else m)
        bh = inner.height() * m
        bx = inner.left() + i * (bar_w + gap)
        painter.drawRect(QRectF(bx, inner.bottom() - bh, bar_w, bh))
    painter.restore()
