import logging

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QMenu

from configs.settings_attr import ATTR_PANEL_CURVE_HIT_PX
from process.capture.menu_pump import exec_menu_capture
from process.widget.overlays.curve_model import (
    CURVE_EASE_LABELS, CURVE_EASE_MODES, EASE_LINEAR,
)
from process.undo import record_attr

logger = logging.getLogger(__name__)

def _curve_points(row) -> list:
    out = []
    for p in (row.spec.get() or []):
        ease = p[2] if len(p) > 2 else EASE_LINEAR
        out.append([float(p[0]), float(p[1]), ease])
    return out

class CurveEditMixin:

    def _curve_nearest(self, row, mx: float, my: float):
        pts = row.spec.get() or []
        best = None
        best_d = None
        for i, p in enumerate(pts):
            px = row.control_x + float(p[0]) * row.control_w
            py = row.control_y + (1.0 - float(p[1])) * row.control_h
            d = ((px - mx) ** 2 + (py - my) ** 2) ** 0.5
            if best_d is None or d < best_d:
                best_d = d
                best = i
        return best, best_d

    def _curve_pick(self, row, mx: float, my: float) -> int | None:
        return self._curve_nearest(row, mx, my)[0]

    def _record_curve(self, row, before: list, after: list) -> None:
        record_attr(self._window, self._rows, row.spec.label, before, after)

    def _curve_reset(self, row, before: list) -> None:
        row.spec.set(row.spec.default)
        after = [tuple(p) for p in (row.spec.get() or [])]
        if row.spec.on_commit is not None:
            row.spec.on_commit()
        self._record_curve(row, before, after)
        self._repaint_live()

    def _curve_context(self, row, mx: float, my: float) -> None:
        pts = _curve_points(row)
        before = [tuple(p) for p in pts]
        idx, dist = self._curve_nearest(row, mx, my)
        near = (dist is not None and dist <= ATTR_PANEL_CURVE_HIT_PX
                and idx is not None)
        widget = self._surface
        menu = QMenu(widget)
        ease_acts = {}
        act_add = act_del = None
        if near:
            cur = pts[idx][2]
            for mode in CURVE_EASE_MODES:
                act = menu.addAction(CURVE_EASE_LABELS[mode])
                act.setCheckable(True)
                act.setChecked(mode == cur)
                ease_acts[act] = mode
            menu.addSeparator()
            act_del = menu.addAction('Remove Point')
            act_del.setEnabled(0 < idx < len(pts) - 1)
        else:
            act_add = menu.addAction('Add Point')
        act_reset = None
        if row.spec.default is not None:
            menu.addSeparator()
            act_reset = menu.addAction('Reset to default')
        chosen = exec_menu_capture(
            self._window, menu,
            widget.mapToGlobal(QPoint(int(mx), int(my))),
        )
        if chosen is None:
            return
        if chosen is act_reset:
            self._curve_reset(row, before)
            return
        if chosen in ease_acts:
            pts[idx][2] = ease_acts[chosen]
        elif chosen is act_del and act_del.isEnabled():
            del pts[idx]
        elif chosen is act_add:
            cx = min(1.0, max(0.0, (mx - row.control_x)
                              / max(1.0, row.control_w)))
            cy = min(1.0, max(0.0, 1.0 - (my - row.control_y)
                              / max(1.0, row.control_h)))
            pts.append([cx, cy, EASE_LINEAR])
            pts.sort(key=lambda p: p[0])
        else:
            return
        after = [tuple(p) for p in pts]
        row.spec.set(after)
        if row.spec.on_commit is not None:
            row.spec.on_commit()
        self._record_curve(row, before, after)
        self._repaint_live()

    def _curve_apply(self, row, mx: float, my: float) -> None:
        idx = self._curve_idx
        pts = _curve_points(row)
        if idx is None or not pts:
            return
        cx = (mx - row.control_x) / max(1.0, row.control_w)
        cy = 1.0 - (my - row.control_y) / max(1.0, row.control_h)
        cy = min(1.0, max(0.0, cy))
        n = len(pts)
        if idx == 0:
            cx = 0.0
        elif idx == n - 1:
            cx = 1.0
        else:
            lo = pts[idx - 1][0] + 0.001
            hi = pts[idx + 1][0] - 0.001
            cx = min(hi, max(lo, cx))
        pts[idx] = [cx, cy, pts[idx][2]]
        row.spec.set([tuple(p) for p in pts])
        self._repaint_live()
