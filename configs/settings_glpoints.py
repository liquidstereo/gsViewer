# -- PLY Header Detection --
PLY_HEADER_PROBE_BYTES: int = 65536
GAUSSIAN_PROPERTY_PREFIXES: tuple[str, ...] = (
    'f_dc_', 'f_rest_', 'scale_', 'rot_',
)
# -- Colors --
POINTCLOUD_DEFAULT_COLOR: str = '#D0D0D0'
POINTCLOUD_COLOR_KEYS: tuple[tuple[str, str, str], ...] = (
    ('red', 'green', 'blue'),
    ('diffuse_red', 'diffuse_green', 'diffuse_blue'),
)
POINTCLOUD_COLOR_UINT8_SCALE: float = 255.0
# -- GL Offscreen Render --
GLPOINTS_GL_MAJOR: int = 3
GLPOINTS_GL_MINOR: int = 3
GLPOINTS_DEPTH_BITS: int = 24
GLPOINTS_POINT_SIZE: float = 2.0
# -- Plugin Opacity Gating --
GLPOINTS_OPACITY_MIN: float = 0.5
