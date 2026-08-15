import math
from process.common.axis_rot import build_world_rot, build_world_rot_presets
# -- Clipping / FOV --
NEAR_PLANE: float = 0.01
FAR_PLANE: float = 100.0
FOV_X_DEG: float = 75.0
# -- Camera Initial Values --
CAM_DOLLY: float | str = 'Auto'
CAM_ZOOM: float = 2.15
CAM_FOCAL_LENGTH: float | str = 'Auto'
CAM_DIST_FACTOR: float = 3.275
STARTUP_CAM_POSITION: list[float] = [0, 0, 0]
# -- Camera Control Speed --
ORBIT_SPEED: float = 0.005
PAN_SPEED: float = 0.001
ZOOM_SPEED: float = 0.1
EL_CLAMP: float = math.pi / 2.0 - 0.01
# -- Turntable (Camera Auto-rotate) --
TURNTABLE: bool = False
TURNTABLE_SPEED: int = 18
STARTUP_CAM_DEGREE: int = 120
# -- Coordinate Transform --
CAM_UP: str = '+Y'
CAM_FORWARD: str = '+Z'
WORLD_ROT: tuple[tuple[float, ...], ...] = build_world_rot(
    CAM_UP, CAM_FORWARD
)
WORLD_ROT_PAIRS: tuple[tuple[str, str], ...] = (
    ('+Y', '+Z'),
    ('-Y', '-Z'),
    ('-Z', '+Y'),
    ('+Z', '-Y'),
)
WORLD_ROT_PRESETS: tuple[tuple[tuple[float, ...], ...], ...] = (
    build_world_rot_presets(WORLD_ROT_PAIRS)
)
WORLD_ROT_NAMES: tuple[str, ...] = ('X+90', 'X-90', 'YZ-flip', 'Identity')
