from configs.settings_typo import FONT_PRIORITY
# -- Viewer Window --
WINDOW_WIDTH: int  = 1080
ASPECT_RATIO: float  = 1.49074
WINDOW_HEIGHT: int = round(WINDOW_WIDTH * ASPECT_RATIO)
SET_WINDOW_FIXED_SIZE: bool = True
DISABLE_MAXIMIZE_BUTTON: bool = True
CLOSE_DIALOG: bool = False
# -- Window Display Downscale --
FORCE_RESIZE_WINDOW: bool = True
RESIZE_MAX_HEIGHT: int = 1080
# -- Responsive Overlay Scale Base --
RESPONSIVE_BASE_HEIGHT: int = RESIZE_MAX_HEIGHT
# -- Render Quality --
ANTIALIAS: bool = True
# -- FPS Display --
FPS_ALPHA: float   = 0.1
# -- Bounding Box --
BBOX_LINE_WIDTH: int = 1
BBOX_LINE_ALPHA: float = 0.50
# -- Grid --
GRID_LINE_WIDTH: int = 1
GRID_DIVISIONS: int  = 5
GRID_LINE_ALPHA: float = 0.50
GRID_PANE_ALPHA: float = 0.00
# -- Startup Display State --
STARTUP_BBOX: bool     = False
STARTUP_GRID: bool     = False
DEPTH_OCCLUSION: bool  = False
STARTUP_ANNOTATION: bool = False
STARTUP_MODE: str | None = None
STARTUP_GRID_TICKS: bool  = False
STARTUP_GRID_LABELS: bool = False
# -- Script Console Editor --
CONSOLE_WINDOW_COLS: int = 70
CONSOLE_WIDTH_PADDING: int = 4
CONSOLE_WINDOW_H: int    = 300
CONSOLE_FONT_FAMILY: tuple[str, ...] = FONT_PRIORITY
CONSOLE_TAB_SPACES: int  = 4
CONSOLE_APPLY_DEBOUNCE_MS: int = 300
# -- Plugin Effect Settings --
