from configs.settings_window import WINDOW_WIDTH
# -- Fog Master Switch --
FOG_ENABLED: bool      = False
POINT_FOG_ENABLED: bool = False
# -- Fog Parameters --
FOG_DENSITY: float           = 0.25
FOG_START: float             = 0.0
FOG_THRESHOLD: float         = 1.0
FOG_THRESHOLD_DENSITY: float = 1.0
FOG_POINT_BG: bool          = True
FOG_POINT_BG_DENSITY: float  = 7.5
# -- Super-sampling AA --
SSAA_SCALE: int = 1
# -- Depth of Field --
DOF_ENABLED: bool    = False
DOF_FOCUS_DIST: float = 3.0
DOF_APERTURE: float   = 0.1
DOF_MAX_BLUR: int   = 15
# -- Exposure Control --
EXPOSURE: float = 1.0
# -- Sharpen --
SHARPEN_ENABLED: bool = True
SHARPEN_AMOUNT: float  = 7.0
SHARPEN_RADIUS: int  = 1
# -- Bloom / Glow --
BLOOM_ENABLED: bool    = False
BLOOM_THRESHOLD: int  = 200
BLOOM_INTENSITY: float  = 0.5
BLOOM_RADIUS: int     = 15
# -- Dilation / Erosion --
DILATE_SCALE: float = WINDOW_WIDTH * 0.00075
POINT_SCALE: float = 0.003
# -- Splat Scale Factor --
SPLAT_SCALE_DEFAULT: float = 1.0
SPLAT_SCALE_FACTOR: float  = 1.1
SPLAT_SCALE_MIN: float     = 0.001
SPLAT_SCALE_MAX: float     = 3.0
# -- Clipping / Sectioning --
CLIP_ENABLED: bool = False
CLIP_AXIS: str    = 'Z'
CLIP_MIN: float     = -999.0
CLIP_MAX: float     = 0.0
# -- Global Opacity --
GLOBAL_OPACITY: float = 1.0
# -- Toon Shading --
TOON_ENABLED: bool = False
TOON_STEPS: int   = 4
