from configs.settings_window import ASPECT_RATIO, RESPONSIVE_BASE_HEIGHT
from configs.settings_overlay import (
    COMMENT_OVERLAY_TEXT_SIZE, LOADING_OVERLAY_TEXT_SIZE,
    MESSAGE_OVERLAY_TEXT_SIZE, OVERLAY_LOG_SIZE, OVERLAY_TEXT_SIZE,
    PANEL_TITLE_SIZE, STATUS_OVERLAY_TEXTSIZE, AXIS_INDICATOR_ARROW_WIDTH,
    AXIS_INDICATOR_CONE_SIZE, AXIS_INDICATOR_LABEL_GAP,
    AXIS_INDICATOR_LABEL_RATIO, AXIS_INDICATOR_SCALE, AXIS_INDICATOR_X,
    AXIS_INDICATOR_Y_OFFSET, SEQ_OVERLAY_CORNER_RADIUS, SEQ_OVERLAY_MARGIN,
    SEQ_OVERLAY_W, WAVEFORM_OVERLAY_MARGIN, WAVEFORM_OVERLAY_W,
)
from configs.settings_window import BBOX_LINE_WIDTH, GRID_LINE_WIDTH

_MIN_SCALE: float = 0.25
_MAX_SCALE: float = 4.0

def ui_scale(w: int) -> float:
    if w <= 0:
        return 1.0
    raw = (float(w) * ASPECT_RATIO) / float(RESPONSIVE_BASE_HEIGHT)
    return max(_MIN_SCALE, min(_MAX_SCALE, raw))

def scaled_text_size(w: int) -> int:
    return max(1, round(OVERLAY_TEXT_SIZE * ui_scale(w)))

def scaled_axis_label_size(w: int) -> int:
    return max(1, round(scaled_text_size(w) * AXIS_INDICATOR_LABEL_RATIO))

def scaled_axis_label_gap(w: int) -> int:
    return max(1, round(AXIS_INDICATOR_LABEL_GAP * ui_scale(w)))

def scaled_log_size(w: int) -> int:
    return max(1, round(OVERLAY_LOG_SIZE * ui_scale(w)))

def scaled_comment_size(w: int) -> int:
    return max(1, round(COMMENT_OVERLAY_TEXT_SIZE * ui_scale(w)))

def scaled_message_size(w: int) -> int:
    return max(1, round(MESSAGE_OVERLAY_TEXT_SIZE * ui_scale(w)))

def scaled_status_size(w: int) -> int:
    return max(1, round(STATUS_OVERLAY_TEXTSIZE * ui_scale(w)))

def scaled_loading_size(w: int) -> int:
    return max(1, round(LOADING_OVERLAY_TEXT_SIZE * ui_scale(w)))

def scaled_title_size(w: int) -> int:
    return max(1, round(PANEL_TITLE_SIZE * ui_scale(w)))

def scaled_margin(w: int, base_px: int) -> int:
    return max(1, round(base_px * ui_scale(w)))

def scaled_seq_inset_w(w: int) -> int:
    return max(1, round(SEQ_OVERLAY_W * ui_scale(w)))

def scaled_seq_inset_margin(w: int) -> int:
    return max(1, round(SEQ_OVERLAY_MARGIN * ui_scale(w)))

def scaled_seq_inset_radius(w: int) -> int:
    if SEQ_OVERLAY_CORNER_RADIUS <= 0:
        return 0
    return max(1, round(SEQ_OVERLAY_CORNER_RADIUS * ui_scale(w)))

def scaled_waveform_inset_w(w: int) -> int:
    return max(1, round(WAVEFORM_OVERLAY_W * ui_scale(w)))

def scaled_waveform_inset_margin(w: int) -> int:
    return max(1, round(WAVEFORM_OVERLAY_MARGIN * ui_scale(w)))

def scaled_grid_line_width(w: int) -> int:
    return max(1, round(GRID_LINE_WIDTH * ui_scale(w)))

def scaled_bbox_line_width(w: int) -> int:
    return max(1, round(BBOX_LINE_WIDTH * ui_scale(w)))

def scaled_axis_origin(w: int, h: int) -> tuple[int, int]:
    s = ui_scale(w)
    cx = max(1, round(AXIS_INDICATOR_X * s))
    cy = h - max(1, round(AXIS_INDICATOR_Y_OFFSET * s))
    return cx, cy

def scaled_axis_scale(w: int) -> int:
    return max(1, round(AXIS_INDICATOR_SCALE * ui_scale(w)))

def scaled_axis_arrow_width(w: int) -> int:
    return max(1, round(AXIS_INDICATOR_ARROW_WIDTH * ui_scale(w)))

def scaled_axis_cone_size(w: int) -> int:
    return max(1, round(AXIS_INDICATOR_CONE_SIZE * ui_scale(w)))
