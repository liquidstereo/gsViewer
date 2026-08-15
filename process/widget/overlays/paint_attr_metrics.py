from PySide6.QtGui import QPainter

from configs.settings_attr import (
    ATTR_PANEL_BLOCK_GAP, ATTR_PANEL_BUTTON_H_SCALE,
    ATTR_PANEL_CURVE_ROWS, ATTR_PANEL_DROPDOWN_MARK,
    ATTR_PANEL_GAP, ATTR_PANEL_MARGIN, ATTR_PANEL_PAD,
    ATTR_PANEL_SEP_GAP, ATTR_PANEL_SLIDER_W,
)
from configs.settings_overlay import (
    ATTR_OVERLAY_LINEHEIGHT, OVERLAY_LINE_PAD, OVERLAY_TEXT_LINEHEIGHT,
    PANEL_TITLE_GAP_RATIO, ATTRIBUTE_OVERLAY_WIDTH,
)
from process.widget.overlays.attr_spec import (
    CONSOLE_BUTTON_LABEL, KIND_BUTTON, KIND_CURVE, KIND_CUSTOM, KIND_ENUM,
    KIND_FLOAT, KIND_INT, KIND_LABEL, KIND_METER, STANDARD_BUTTON_LABELS,
    AttrSpec,
)
from process.widget.overlays.paint_attr_button import (
    button_row_width, button_run_count,
)
from process.widget.scale import scaled_margin
from process.widget.text_case import apply_overlay_case

def panel_width_floor(fm, w: int) -> float:
    specs = [AttrSpec(label, KIND_BUTTON) for label in
             STANDARD_BUTTON_LABELS]
    specs.append(AttrSpec(CONSOLE_BUTTON_LABEL, KIND_BUTTON,
                          row_break=True))
    return max(float(scaled_margin(w, ATTRIBUTE_OVERLAY_WIDTH)),
               button_row_width(fm, specs))

def _spec_value_w(fm, sp) -> float:
    if sp.kind == KIND_ENUM:
        cands = [o + ATTR_PANEL_DROPDOWN_MARK for o in sp.options] or ['']
    elif sp.kind in (KIND_FLOAT, KIND_INT, KIND_LABEL, KIND_METER):
        try:
            cands = [sp.fmt.format(sp.vmin), sp.fmt.format(sp.vmax)]
        except (ValueError, TypeError):
            cands = [sp.value_text()]
    else:
        return 0.0
    return max(
        fm.horizontalAdvance(apply_overlay_case(c)) for c in cands)

def _is_collapsed(collapsed: dict | None, sp) -> bool:
    if collapsed is None:
        return sp.collapsed_default
    return collapsed.get(sp.label, sp.collapsed_default)

def _curve_sep_count(specs: list) -> int:
    return sum(
        1 for i, sp in enumerate(specs)
        if sp.kind == KIND_CURVE and i < len(specs) - 1
    )

def _curve_lead_sep_count(specs: list) -> int:
    return sum(
        1 for i, sp in enumerate(specs)
        if sp.kind == KIND_CURVE and i > 0 and specs[i - 1].kind != KIND_CURVE
    )

def _curve_box_count(specs: list, collapsed: dict | None) -> int:
    return sum(
        1 for sp in specs
        if sp.kind == KIND_CURVE and not _is_collapsed(collapsed, sp)
    )

def _custom_lead_sep_count(specs: list) -> int:
    return sum(
        1 for i, sp in enumerate(specs)
        if sp.kind == KIND_CUSTOM and i > 0
    )

def attr_row_line_h(fm) -> int:
    return (round(fm.height() * (ATTR_OVERLAY_LINEHEIGHT
                                 or OVERLAY_TEXT_LINEHEIGHT))
            + OVERLAY_LINE_PAD)

def _panel_metrics(painter: QPainter, w: int, blocks: list, fm,
                   title_fm, collapsed: dict | None = None) -> dict:
    line_h = attr_row_line_h(fm)
    title_gap = round(fm.height() * PANEL_TITLE_GAP_RATIO)
    pad = scaled_margin(w, ATTR_PANEL_PAD)
    gap = scaled_margin(w, ATTR_PANEL_GAP)
    margin = scaled_margin(w, ATTR_PANEL_MARGIN)
    slider_w = scaled_margin(w, ATTR_PANEL_SLIDER_W)
    sep_gap = scaled_margin(w, ATTR_PANEL_SEP_GAP)
    label_w = 0
    value_w = 0
    title_w = 0
    btn_w = 0
    n_rows = 0
    n_btn_runs = 0
    n_curve_seps = 0
    n_curve_lead_seps = 0
    n_curve_box_gaps = 0
    n_custom_lead_seps = 0
    n_titles = 0
    n_block_seps = 0
    for bi, (title, specs) in enumerate(blocks):
        has_title = bool(title)
        if has_title:
            title_w = max(title_w, title_fm.horizontalAdvance(
                apply_overlay_case(title)))
            n_titles += 1
            if bi > 0:
                n_block_seps += 1
        n_rows += (1 if has_title else 0) + _row_count(specs, collapsed)
        n_btn_runs += button_run_count(specs)
        n_curve_seps += _curve_sep_count(specs)
        n_curve_lead_seps += _curve_lead_sep_count(specs)
        n_curve_box_gaps += _curve_box_count(specs, collapsed)
        n_custom_lead_seps += _custom_lead_sep_count(specs)
        btn_w = max(btn_w, button_row_width(fm, specs))
        for sp in specs:
            if sp.kind == KIND_BUTTON:
                continue
            label_w = max(label_w, fm.horizontalAdvance(
                apply_overlay_case(sp.label)))
            value_w = max(value_w, _spec_value_w(fm, sp))
    content_w = max(
        title_w, label_w + gap + slider_w + gap + value_w, btn_w)

    content_w = max(content_w, panel_width_floor(fm, w))
    panel_w = content_w + pad * 2
    block_gap = scaled_margin(w, ATTR_PANEL_BLOCK_GAP)

    btn_extra_h = fm.height() * (ATTR_PANEL_BUTTON_H_SCALE - 1.0)

    n_seps = (n_block_seps + n_btn_runs + n_curve_seps
              + n_curve_lead_seps + n_curve_box_gaps + n_custom_lead_seps)

    lh_extra = line_h - OVERLAY_LINE_PAD - fm.height()
    panel_h = (
        pad * 2 + line_h * n_rows
        + block_gap * n_block_seps + sep_gap * n_seps
        + btn_extra_h * n_btn_runs + title_gap * n_titles
        - lh_extra
    )
    return {
        'line_h': line_h, 'pad': pad, 'gap': gap, 'slider_w': slider_w,
        'label_w': label_w, 'panel_w': panel_w, 'panel_h': panel_h,
        'x0': w - panel_w - margin, 'y0': margin, 'ascent': fm.ascent(),
        'block_gap': block_gap, 'sep_gap': sep_gap,
        'btn_extra_h': btn_extra_h, 'title_gap': title_gap,
    }

def _row_count(specs: list, collapsed: dict | None = None) -> int:
    n = 0
    i = 0
    while i < len(specs):
        if specs[i].kind == KIND_BUTTON:
            i += 1
            while (i < len(specs) and specs[i].kind == KIND_BUTTON
                   and not specs[i].row_break):
                i += 1
            n += 1
        elif specs[i].kind == KIND_CURVE:

            n += 1
            if not _is_collapsed(collapsed, specs[i]):
                n += ATTR_PANEL_CURVE_ROWS
            i += 1
        elif specs[i].kind == KIND_CUSTOM:

            n += specs[i].custom_rows
            i += 1

            if i < len(specs):
                n += 1
        else:
            n += 1
            i += 1
    return n
