import logging

from PySide6.QtCore import Qt, QTimer

from process.scroll.overlay_scroll import (
    OverlayScrollArea, SCROLLBAR_GAP, SCROLLBAR_WIDTH,
)
from process.widget.overlays.attr_editor import AttributeEditorMouseHandler
from process.widget.overlays.paint_attribute import (
    measure_attribute_panel, paint_attribute_sections,
)
from process.widget.scale import scaled_margin
from configs.settings_attr import ATTR_PANEL_MARGIN
from configs.settings_overlay import STARTUP_ATTR_OVERLAY

logger = logging.getLogger(__name__)

class AttrScrollHost:

    def __init__(self, window) -> None:
        self._window = window
        widget = window._widget
        self._scroll = OverlayScrollArea(
            self._paint, self._on_mouse, parent=widget)
        self._content = self._scroll.content

        self._content._attr_rows = []
        self._content._attr_pressed_label = None
        self._content._curve_collapsed = {}
        self._content._mouse_pos = None
        self._content._attr_panel_rect = None
        self._handler = AttributeEditorMouseHandler(
            window, surface=self._content)
        self._last_size: tuple = (0, 0)
        self._scroll.hide()

    def _paint(self, painter, w: int, h: int) -> None:
        sections = self._sections()
        if not sections:
            self._content._attr_rows = []
            return
        scale_w = self._window._widget.width()
        self._content._attr_rows = paint_attribute_sections(
            painter, scale_w, h, sections,
            mouse_pos=self._content._mouse_pos,
            pressed_label=self._content._attr_pressed_label,
            collapsed=self._content._curve_collapsed,
            widget=self._content, origin=(0, 0),
        )

    def _on_mouse(self, kind: str, event) -> bool:
        if kind == 'move':
            pos = event.position()
            self._content._mouse_pos = (pos.x(), pos.y())
        consumed = self._handler.handle(kind, event)
        if kind == 'move':
            self._update_cursor(event)
            self._content.update()
        return consumed

    def _update_cursor(self, event) -> None:
        pos = event.position()
        on = any(r.hit(pos.x(), pos.y()) for r in self._content._attr_rows)
        if on:
            self._content.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._content.unsetCursor()

    def _sections(self) -> list | None:
        widget = self._window._widget
        if getattr(widget, '_attr_overlay_hidden', False):
            return None
        if getattr(widget, '_compact_overlays', False):
            return None
        return getattr(self._window, '_attr_sections', None) or None

    def frame_tick(self, painter, w: int, h: int, depth) -> None:
        sections = self._sections()
        if not sections:
            if self._scroll.isVisible():
                QTimer.singleShot(0, self.sync)
            return
        pw, ph = measure_attribute_panel(
            self._window._widget.width(), sections,
            self._content._curve_collapsed)
        if (pw, ph) != self._last_size or not self._scroll.isVisible():
            QTimer.singleShot(0, self.sync)
        self._content.update()

    def sync(self) -> None:
        widget = self._window._widget
        sections = self._sections()
        if not sections:
            self._scroll.hide()
            self._last_size = (0, 0)
            return
        scale_w = widget.width()
        pw, ph = measure_attribute_panel(
            scale_w, sections, self._content._curve_collapsed)
        if pw <= 0 or ph <= 0:
            self._scroll.hide()
            self._last_size = (0, 0)
            return
        self._last_size = (pw, ph)
        self._scroll.set_content_size(pw, ph)
        margin = int(scaled_margin(scale_w, ATTR_PANEL_MARGIN))
        avail_h = max(widget.height() - margin * 2, 1)
        view_h = int(min(ph, avail_h))

        if ph > avail_h:
            total_w = int(pw + SCROLLBAR_GAP + SCROLLBAR_WIDTH)
        else:
            total_w = int(pw)
        x = widget.width() - total_w - margin
        self._scroll.setGeometry(int(x), margin, total_w, view_h)
        self._scroll.show()
        self._scroll.raise_()
        self._content.update()

def register_attr_scroll_host(window) -> AttrScrollHost:
    if not hasattr(window, '_attr_sections'):
        window._attr_sections = []
    widget = window._widget
    if not hasattr(widget, '_attr_overlay_hidden'):

        widget._attr_overlay_hidden = not STARTUP_ATTR_OVERLAY

    if getattr(window, '_audio_selected', False):
        widget._attr_overlay_hidden = False
    host = AttrScrollHost(window)
    ovs = getattr(widget, '_overlay_painters', None)
    if ovs is not None:
        ovs.append(host.frame_tick)
    rcb = getattr(widget, '_resize_cbs', None)
    if rcb is not None:
        rcb.append(host.sync)
    QTimer.singleShot(0, host.sync)
    logger.info('Attribute scroll host attached (overlay-only scrollbar)')
    return host
