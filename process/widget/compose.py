import logging
import time

from configs.settings_overlay import (
    MESSAGE_OVERLAY_BUF_CHAR, MESSAGE_OVERLAY_POSITION,
    MESSAGE_OVERLAY_VISIBILITY, REC_INDICATOR_TEXT,
)
from process.common.timefmt import fmt_mmss_ms
from process.widget.overlays.paint_text import REC_DOT_CHAR
import process.widget.paint as widget_paint
from process.widget.overlays import (
    paint_gizmo_overlay, paint_log_overlay, paint_comment_overlay,
    paint_overlay_text,
)
from process.widget.overlays.paint_waveform_overlay import (
    paint_waveform_overlay,
)
from process.annotation.paint import paint_annotations as _paint_annotations

logger = logging.getLogger(__name__)

def paint_overlay_stack(widget, painter, w, h, dbg, ck) -> None:
    if widget._overlays_visible:
        if widget._depth_buffer is not None:
            widget_paint.paint_depth_correct_overlays(
                painter, widget._bbox_lines, widget._grid_data,
                widget._depth_buffer, w, h,
            )
        else:
            widget_paint.paint_grid(painter, widget._grid_data, w)
            widget_paint.paint_bbox(painter, widget._bbox_lines, w)
        if dbg:
            ck.append(('gridbbox', time.perf_counter()))

        if not widget._compact_overlays:
            for _i, fn in enumerate(widget._underlay_painters):
                try:
                    fn(painter, w, h, widget._depth_buffer)
                except Exception:
                    logger.exception('Underlay painter error')
                if dbg:
                    _mod = getattr(fn, '__module__', '?').split('.')[-2:]
                    ck.append(
                        (f'ul{_i}:{".".join(_mod)}',
                         time.perf_counter()))
        if dbg:
            ck.append(('underlay_end', time.perf_counter()))

        if widget._sequence_overlay_visible:
            widget_paint.paint_seq_inset(
                painter, widget._seq_frame, widget._seq_opacity, w, h,
            )

        if widget._waveform_overlay_visible:
            paint_waveform_overlay(
                painter, widget._waveform_source,
                (widget._seq_frame
                 if widget._sequence_overlay_visible else None),
                w, h,
            )
        if dbg:
            ck.append(('seq', time.perf_counter()))
        text_on = widget._text_overlay_visible
        msg_on = (text_on and MESSAGE_OVERLAY_VISIBILITY
                  and bool(widget._message_overlay))

        msg_bottom = msg_on and MESSAGE_OVERLAY_POSITION == 'bottom'
        msg_left = msg_on and not msg_bottom

        rec_active = bool(getattr(widget, '_live_rec_on', False))
        rec_dot = bool(getattr(widget, '_live_rec_dot', False))
        log_n = len(widget._log_overlay) if text_on else 0
        if text_on and widget._log_overlay:
            paint_log_overlay(painter, widget._log_overlay, w, h)
        if dbg:
            ck.append(('log', time.perf_counter()))
        if widget._colormap_bar:
            widget_paint.paint_colormap_bar(
                painter, widget._colormap_bar, w, h,
            )
        if widget._annotations:
            _paint_annotations(painter, widget._annotations)
        if widget._object_kf_markers:
            _paint_annotations(painter, widget._object_kf_markers)
        if widget._global_kf_markers:
            _paint_annotations(painter, widget._global_kf_markers)

        for fn in widget._overlay_painters:
            try:
                fn(painter, w, h, widget._depth_buffer)
            except Exception:
                logger.exception('Overlay painter error')
        if dbg:
            ck.append(('cmap+ovlpaint', time.perf_counter()))
        comment_on = bool(widget._comment_overlay) and text_on

        rec_seg = ''
        if text_on and rec_active:

            rec_seg = REC_INDICATOR_TEXT + REC_DOT_CHAR
            rec_sec = getattr(widget, '_live_rec_seconds', None)
            if rec_sec is not None:
                rec_seg += f' ({fmt_mmss_ms(rec_sec)})'
        tail = widget._message_overlay if msg_bottom else ''
        if rec_seg:
            tail = (tail + MESSAGE_OVERLAY_BUF_CHAR + rec_seg
                    if tail else rec_seg)

        if text_on:
            paint_comment_overlay(
                painter, widget._comment_overlay if comment_on else '',
                w, h, log_n, widget._render_mode, append_msg=tail,
                dot_visible=(rec_dot if rec_seg else True),
            )

        if widget._gizmo_overlay_visible and widget._gizmo_overlay:

            gizmo_dy = widget._bottom_gizmo_offset(w, log_n, text_on, False)
            paint_gizmo_overlay(
                painter, widget._gizmo_overlay, w, y_offset=gizmo_dy,
            )
        if dbg:
            ck.append(('comment+gizmo', time.perf_counter()))
        if text_on:
            (widget._region_rows, widget._object_rows,
             widget._audio_rows) = paint_overlay_text(
                painter, widget._info_overlay, widget._cam_overlay,
                widget._objinfo_overlay, widget._status_overlay,
                widget._stat_overlay, w, widget._render_mode,
                region_items=widget._region_items,
                object_items=widget._object_items,
                message=(widget._message_overlay if msg_left else ''),
                region_hover=widget._region_hover_index,
                object_hover=widget._object_hover_index,
                audio_items=widget._audio_items,
                audio_hover=widget._audio_hover_index,
            )
        else:
            widget._region_rows = []
            widget._object_rows = []
            widget._audio_rows = []
        if dbg:
            ck.append(('text+message', time.perf_counter()))
