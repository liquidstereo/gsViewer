import logging
import time

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontMetrics, QImage, QPainter, QPalette
from PySide6.QtWidgets import QWidget

from process.common.font import make_font
from configs.settings_window import ANTIALIAS
from configs.settings_overlay import (
    STARTUP_GIZMO_OVERLAY, STARTUP_SEQUENCE_OVERLAY, STARTUP_TEXT_OVERLAY,
    STARTUP_WAVEFORM_OVERLAY, DISPLAY_INFO_OVERLAY, DISPLAY_STAT_OVERLAY,
    DISPLAY_CAM_OVERLAY, DISPLAY_OBJINFO_OVERLAY, DISPLAY_STATUS_OVERLAY,
    DISPLAY_GIZMO_OVERLAY, DISPLAY_MESSAGE_OVERLAY, DISPLAY_COMMENT_OVERLAY,
    DISPLAY_LOG_OVERLAY, DISPLAY_SEQUENCE_OVERLAY, DISPLAY_WAVEFORM_OVERLAY,
)
from configs.settings_color import BACKGROUND_COLOR
import process.widget.paint as widget_paint
from process.widget.compose import paint_overlay_stack
from process.widget.scale import scaled_text_size
import process.widget.paint_help as widget_paint_help
from process.widget.loading_host import LoadingOverlayHost

logger = logging.getLogger(__name__)

class SplatWidget(QWidget):
    def __init__(self, cam_callback, parent=None):
        super().__init__(parent)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(BACKGROUND_COLOR))
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self._image: QImage | None = None

        self._image_arr: np.ndarray | None = None

        self._pp_paint_n: int = 0
        self._pp_paint_ms: float = 0.0
        self._pp_paint_end: float = 0.0
        self._info_overlay: str = ''
        self._stat_overlay: str = ''
        self._cam_overlay: str = ''
        self._objinfo_overlay: str = ''
        self._status_overlay: str = ''
        self._render_mode: int = 0
        self._bbox_lines: list = []
        self._grid_data: dict = {}
        self._gizmo_overlay: list = []
        self._depth_buffer: np.ndarray | None = None
        self._seq_frame: np.ndarray | None = None
        self._seq_opacity: float = 0.0

        self._waveform_source = None
        self._log_overlay: list[tuple[int, str]] = []
        self._comment_overlay: str = ''
        self._colormap_bar: dict | None = None
        self._annotations: list[tuple[int, int, str]] = []
        self._object_kf_markers: list[tuple[int, int, str]] = []
        self._global_kf_markers: list[tuple[int, int, str]] = []
        self._message_overlay: str | None = None

        self._live_rec_on: bool = False
        self._live_rec_dot: bool = False

        self._live_rec_seconds: float | None = None

        self._live_rec_message: str | None = None

        self._loading_overlay: str | None = None
        self._loading_host = LoadingOverlayHost(self)

        self._region_items: list = []
        self._region_rows: list = []

        self._region_hover_index: int | None = None

        self._object_items: list = []
        self._object_rows: list = []
        self._object_hover_index: int | None = None

        self._audio_items: list = []
        self._audio_rows: list = []
        self._audio_hover_index: int | None = None

        self._attr_rows: list = []

        self._mouse_pos: tuple | None = None
        self._attr_pressed_label: str | None = None
        self._was_on_clickable: bool = False
        self._overlays_visible: bool = True

        self._compact_overlays: bool = False
        self._text_overlay_visible: bool = STARTUP_TEXT_OVERLAY
        self._gizmo_overlay_visible: bool = STARTUP_GIZMO_OVERLAY
        self._sequence_overlay_visible: bool = STARTUP_SEQUENCE_OVERLAY
        self._waveform_overlay_visible: bool = STARTUP_WAVEFORM_OVERLAY
        self._show_help: bool = False
        self._help_page: int = 0
        self._show_plugin_help: bool = False
        self._plugin_help_sections: list[tuple[str, list]] = []
        self._plugin_help_page: int = 0
        self._cam_cb = cam_callback

        self._underlay_painters: list = []
        self._overlay_painters: list = []

        self._resize_cbs: list = []

        self._first_paint_cb = None
        self._first_paint_done: bool = False
        self.setMouseTracking(True)

    def set_first_paint_callback(self, fn) -> None:
        self._first_paint_cb = fn

    def set_image(self, arr: np.ndarray) -> None:

        h, w, _ = arr.shape
        self._image_arr = arr
        self._image = QImage(
            arr.data, w, h, w * 3, QImage.Format.Format_RGB888
        )
        self.update()

    def set_info_overlay(self, text: str) -> None:
        self._info_overlay = text if DISPLAY_INFO_OVERLAY else ''

    def set_stat_overlay(self, text: str) -> None:
        self._stat_overlay = text if DISPLAY_STAT_OVERLAY else ''

    def set_cam_overlay(self, text: str) -> None:
        self._cam_overlay = text if DISPLAY_CAM_OVERLAY else ''

    def set_objinfo_overlay(self, text: str) -> None:
        self._objinfo_overlay = text if DISPLAY_OBJINFO_OVERLAY else ''

    def set_status_overlay(self, text: str) -> None:
        self._status_overlay = text if DISPLAY_STATUS_OVERLAY else ''

    def set_render_mode(self, mode: int) -> None:
        self._render_mode = mode

    def set_bbox_lines(
        self, lines: list[tuple[int, int, float, int, int, float]] | None
    ) -> None:
        self._bbox_lines = lines or []

    def set_grid(self, data: dict[str, list] | None) -> None:
        self._grid_data = data or {}

    def set_gizmo_overlay(
        self, data: list[tuple[int, int, int, int, str, str]],
    ) -> None:
        self._gizmo_overlay = data if DISPLAY_GIZMO_OVERLAY else []

    def set_depth_buffer(self, depth: np.ndarray | None) -> None:
        self._depth_buffer = depth

    def set_seq_frame(
        self, frame: np.ndarray | None, opacity: float,
    ) -> None:
        if not DISPLAY_SEQUENCE_OVERLAY:
            frame, opacity = None, 0.0
        self._seq_frame = frame
        self._seq_opacity = opacity

    def set_waveform_source(self, source) -> None:
        self._waveform_source = source if DISPLAY_WAVEFORM_OVERLAY else None

    def set_log_overlay(self, lines: list[tuple[int, str]]) -> None:
        self._log_overlay = lines if DISPLAY_LOG_OVERLAY else []

    def set_comment_overlay(self, text: str) -> None:
        self._comment_overlay = text if DISPLAY_COMMENT_OVERLAY else ''

    def set_colormap_bar(self, info: dict | None) -> None:
        self._colormap_bar = info

    def set_overlays_visible(self, visible: bool) -> None:
        self._overlays_visible = visible

    def set_help_visible(self, visible: bool) -> None:
        self._show_help = visible

    def set_help_page(self, page: int) -> None:
        self._help_page = page

    def set_plugin_help_visible(self, visible: bool) -> None:
        self._show_plugin_help = visible

    def set_plugin_help_sections(
        self, sections: list[tuple[str, list]],
    ) -> None:
        self._plugin_help_sections = sections

    def set_plugin_help_page(self, page: int) -> None:
        self._plugin_help_page = page

    def set_annotations(
        self, markers: list[tuple[int, int, str]],
    ) -> None:
        self._annotations = markers

    def set_object_kf_markers(
        self, markers: list[tuple[int, int, str]],
    ) -> None:
        self._object_kf_markers = markers

    def set_global_kf_markers(
        self, markers: list[tuple[int, int, str]],
    ) -> None:
        self._global_kf_markers = markers

    def set_message_overlay(self, text: str | None) -> None:
        self._message_overlay = text if DISPLAY_MESSAGE_OVERLAY else None

    def set_loading_overlay(self, text: str | None) -> None:
        self._loading_overlay = text
        self._loading_host.set_text(text)

    def set_region_list(self, items: list) -> None:
        self._region_items = items or []

    def set_object_list(self, items: list) -> None:
        self._object_items = items or []

    def set_audio_list(self, items: list) -> None:
        self._audio_items = items or []

    def _bottom_gizmo_offset(
        self, w: int, log_n: int, comment_on: bool, msg_on: bool = False,
    ) -> int:
        upper = log_n + (2 if comment_on else 0) + (1 if msg_on else 0)
        if upper == 0:
            return 0
        f = make_font()
        f.setPointSize(scaled_text_size(w))
        lh = QFontMetrics(f).height() + 2
        return lh * upper

    def paintEvent(self, event) -> None:
        if self._image is None:
            return
        _t_paint = time.perf_counter()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, ANTIALIAS)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, ANTIALIAS)
        painter.drawImage(0, 0, self._image)
        _t_draw = time.perf_counter()
        widget_paint.begin_overlay(painter)
        w, h = self.width(), self.height()
        _dbg = logger.isEnabledFor(logging.DEBUG)
        _ck: list = [('begin', time.perf_counter())]
        paint_overlay_stack(self, painter, w, h, _dbg, _ck)
        if self._show_help:
            widget_paint_help.paint_help_overlay(
                painter, w, h, self._help_page,
            )
        if self._show_plugin_help:
            widget_paint_help.paint_plugin_help_overlay(
                painter, w, h, self._plugin_help_sections,
                self._plugin_help_page,
            )
        painter.end()

        _pp_end = time.perf_counter()
        self._pp_paint_n += 1
        self._pp_paint_ms += (_pp_end - _t_paint) * 1000.0
        self._pp_paint_end = _pp_end
        if logger.isEnabledFor(logging.DEBUG):
            _now = time.perf_counter()
            _splits = ' '.join(
                f'{_ck[i + 1][0]}={(_ck[i + 1][1] - _ck[i][1]) * 1000.0:.1f}'
                for i in range(len(_ck) - 1)
            )
            logger.debug(
                'PERF paintEvent draw %.2fms overlay %.2fms total %.2fms '
                '[%s] dpr=%.2f img=%dx%d widget=%dx%d',
                (_t_draw - _t_paint) * 1000.0,
                (_now - _t_draw) * 1000.0,
                (_now - _t_paint) * 1000.0,
                _splits,
                self.devicePixelRatioF(),
                self._image.width(), self._image.height(),
                self.width(), self.height(),
            )
        if not self._first_paint_done:
            self._first_paint_done = True
            if self._first_paint_cb is not None:
                try:
                    self._first_paint_cb()
                except Exception:
                    logger.exception('First paint callback error')

    def resizeEvent(self, event) -> None:
        self._loading_host.sync_geometry()
        for cb in self._resize_cbs:
            try:
                cb()
            except Exception:
                logger.exception('Resize callback error')
        super().resizeEvent(event)

    def mousePressEvent(self, event) -> None:
        self._cam_cb('press', event)

    def _point_on_clickable(self, x: float, y: float) -> bool:
        for row in self._attr_rows or []:
            if row.hit(x, y):
                return True
        for rows in (self._region_rows, self._object_rows, self._audio_rows):
            for rx, ry, rw, rh, _idx in rows or []:
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    return True
        return False

    def _hovered_region_index(self, x: float, y: float) -> int | None:
        for rx, ry, rw, rh, idx in self._region_rows or []:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return idx
        return None

    def _hovered_object_index(self, x: float, y: float) -> int | None:
        for rx, ry, rw, rh, idx in self._object_rows or []:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return idx
        return None

    def _hovered_audio_index(self, x: float, y: float) -> int | None:
        for rx, ry, rw, rh, idx in self._audio_rows or []:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return idx
        return None

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        self._mouse_pos = (pos.x(), pos.y())
        on_clickable = self._point_on_clickable(pos.x(), pos.y())
        hover_idx = self._hovered_region_index(pos.x(), pos.y())
        if hover_idx != self._region_hover_index:
            self._region_hover_index = hover_idx
            self.update()
        obj_hover_idx = self._hovered_object_index(pos.x(), pos.y())
        if obj_hover_idx != self._object_hover_index:
            self._object_hover_index = obj_hover_idx
            self.update()
        aud_hover_idx = self._hovered_audio_index(pos.x(), pos.y())
        if aud_hover_idx != self._audio_hover_index:
            self._audio_hover_index = aud_hover_idx
            self.update()
        if on_clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

        if on_clickable or self._was_on_clickable:
            self.update()
        self._was_on_clickable = on_clickable
        self._cam_cb('move', event)

    def mouseReleaseEvent(self, event) -> None:
        self._cam_cb('release', event)

    def wheelEvent(self, event) -> None:
        self._cam_cb('wheel', event)
