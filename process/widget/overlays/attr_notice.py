from process.data.pointcloud_caps import notify_if_unsupported

class AttrNoticeMixin:

    def _section_provider(self, row):
        title = row.section or ''
        for section in getattr(self._window, '_attr_sections', ()) or ():
            if section.title_text() == title:
                return section.provider
        return None

    def _press_and_notice(self, event) -> bool:
        pos = event.position()
        row = self._find(pos.x(), pos.y())
        handled = self._press_row(event)
        if row is not None:
            self._notify_row(row)
        return handled

    def _notify_row(self, row) -> None:
        spec = row.spec
        for callback in (self._section_provider(row), spec.set,
                         spec.action, spec.get):
            if callback is None:
                continue
            if notify_if_unsupported(self._window, callback):
                return
