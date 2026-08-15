from process.common import complement_hex
THEME: str = 'Dark'
_BRIGHT: dict[str, str] = {
    'BG':     '#ECEAE4',
    'BOUND':  '#111111',
    'OVTXT':  '#2C2C2C',
    'SHADOW': '#111111',
    'TICK':   '#AAAAAA',
}
_DARK: dict[str, str] = {
    'BG':     '#1A1A1A',
    'BOUND':  '#DDDDDD',
    'OVTXT':  '#ECEAE4',
    'SHADOW': '#000000',
    'TICK':   '#666666',
}
_T: dict[str, str] = _BRIGHT if THEME == 'Bright' else _DARK
# -- Scene Colors --
# -- Background / Bbox / Grid --
BACKGROUND_COLOR: str      = _T['BG']
BOUNDING_COLOR: str        = _T['BOUND']
BBOX_COLOR: str            = BOUNDING_COLOR
GRID_COLOR_FLOOR: str      = BOUNDING_COLOR
GRID_COLOR_WALL_L: str     = BOUNDING_COLOR
GRID_COLOR_WALL_B: str     = BOUNDING_COLOR
GRID_TICK_COLOR: str       = _T['TICK']
GRID_AXIS_LABEL_COLOR: str = BOUNDING_COLOR
# -- 3D Axis Colors --
AXIS_X_COLOR: str = '#FF5555'
AXIS_Y_COLOR: str = '#55FF55'
AXIS_Z_COLOR: str = '#5599FF'
# -- Selection State Colors --
SELECTED_COLOR: str      = '#77ABD9'
DESELECTED_COLOR: str    = '#7AF7FF'
LOCKED_COLOR: str        = '#808080'
# -- Render Mode Colors / Colormap --
MODE_POINT_COLOR: str = complement_hex(_T['BG'])
MODE_ANISO_CMAP: str        = 'RdYlBu_r'
MODE_DEPTH_CMAP: str        = 'turbo'
MODE_ACCUM_CMAP: str        = 'gray'
MODE_SCALE_CMAP: str        = 'viridis'
MODE_SH_CMAP: str           = 'hot'
MODE_MEDIAN_DEPTH_CMAP: str = 'plasma'
MODE_HIT_COUNT_CMAP: str    = 'hot'
# -- Overlay Colors --
# -- Common Overlay Text --
OVERLAY_TEXT_COLOR: str   = _T['OVTXT']
OVERLAY_TEXT_SHADOW: bool  = False
OVERLAY_SHADOW_COLOR: str = _T['SHADOW']
OVERLAY_HICONTRAST_TEXT_COLOR: str = '#FFFFFF'
# -- Object List Colors --
OBJECT_LIST_SELECTED_COLOR: str = '#FF5555'
OBJECT_LIST_HIDDEN_COLOR: str   = LOCKED_COLOR
OBJECT_LIST_HOVER_COLOR: str    = _T['OVTXT']
REGION_PALETTE_SATURATION: float = 0.85
# -- Region List Colors --
REGION_LIST_SELECTED_COLOR: str = SELECTED_COLOR
REGION_LIST_HIDDEN_COLOR: str   = LOCKED_COLOR
REGION_LIST_HOVER_COLOR: str    = _T['OVTXT']
# -- Gizmo Dot Color --
GIZMO_INDICATOR_DOT_COLOR: str = '#C8C8C8'
# -- Log Overlay Colors --
OVERLAY_LOG_COLOR: str         = '#A1A1A1'
OVERLAY_LOG_WARNING_COLOR: str = '#F26716'
OVERLAY_LOG_ERROR_COLOR: str   = '#FF4444'
# -- Attribute Panel Colors --
ATTR_PANEL_SEPARATOR_COLOR: str = '#000000'
ATTR_PANEL_BUTTON_HOVER_BG: str = '#2A3340'
ATTR_PANEL_BUTTON_CLICK_BG: str = '#3A4A5E'
ATTR_PANEL_HOVER_COLOR: str = '#77ABD9'
# -- Help Panel Colors --
HELP_PANEL_BG_COLOR: str    = '#0F0F0F'
HELP_PANEL_BG_ALPHA: int    = 178
HELP_TITLE_COLOR: str       = '#FFFFFF'
HELP_HEADER_COLOR: str      = '#C8C8C8'
HELP_KEY_COLOR: str         = '#FFD250'
HELP_DESC_COLOR: str        = '#C8C8C8'
# -- Annotation Marker Colors --
ANNOT_PIN_FILL_COLOR: str   = '#FFD228'
ANNOT_PIN_BORDER_COLOR: str = '#282828'
ANNOT_TEXT_BG_COLOR: str    = '#141414'
ANNOT_TEXT_BG_ALPHA: int    = 210
ANNOT_TEXT_FG_COLOR: str    = '#FFFFFF'
ANNOT_LINE_COLOR: str       = '#FFD228'
ANNOT_LINE_ALPHA: int       = 200
# -- Colormap Bar Border Color --
CMAP_BAR_BORDER_COLOR: str = '#B4B4B4'
# -- Message Overlay Colors --
MESSAGE_OVERLAY_BG_COLOR: str   = '#FF5555'
MESSAGE_OVERLAY_TEXT_COLOR: str = _T['OVTXT']
LIVE_REC_INDICATOR_COLOR: str = '#FF5555'
