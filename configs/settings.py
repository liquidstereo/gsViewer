from pathlib import Path
from process.common.core import compute_gpu_ahead, get_worker_count
# -- App Meta --
WINDOW_TITLE: str = 'gsViewer'
# -- Project Root --
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
# -- Base Directories --
INPUT_DIR: Path    = Path('input')
OUTPUT_DIR: Path   = Path('output')
LOGS_DIR: Path     = Path('logs')
CACHE_DIR: Path    = INPUT_DIR / 'cache'
DATA_DIR: Path     = INPUT_DIR / 'data'
SEQUENCE_DIR: Path = INPUT_DIR / 'sequences'
SCREENSHOT_DIR: Path  = OUTPUT_DIR / 'screenshot'
JSON_DIR: Path        = Path('json')
# -- Auto-import Skip Toggles --
IGNORE_AUDIO_INPUT: bool = False
IGNORE_SEQUENCE_INPUT: bool = False
# -- Unified Delete Confirm Dialog Toggle --
DELETE_DIALOG: bool = False
# -- JSON Save / Sync --
ENABLE_INSTANT_JSON_SYNC: bool = True
# -- Logging --
LOG_FORMAT: str = (
    '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d: %(message)s'
)
LOG_MSEC_FORMAT: str = '%s.%03d'
LOG_FILE_LEVEL: str = 'info'
LOG_OVERLAY_LEVEL: str = 'debug'
CONSOLE_LOG: bool = False
# -- Spherical Harmonics (SH) --
SH_C0: float = 0.28209479177387814
SH_C1: float = 0.4886025119029199
SH_C2: tuple[float, ...] = (
    1.0925484305920792,
    -1.0925484305920792,
    0.31539156525252005,
    -1.0925484305920792,
    0.5462742152960396,
)
SH_C3: tuple[float, ...] = (
    -0.5900435899266435,
    2.890611442640554,
    -0.4570457994644658,
    0.3731763325901154,
    -0.4570457994644658,
    1.4453057213600776,
    -0.5900435899266435,
)
# -- Static Opacity Pruning --
OPACITY_PRUNE_ENABLED: bool = True
OPACITY_PRUNE_THRESHOLD: float = 0.01
# -- Stride Downsampling --
ENABLE_STRIDE_SLICING: bool = False
SLICING_RATIO: float = 1.0
SLICE_RATIO_STEP: float = 0.1
SLICE_RATIO_MIN: float = 0.0
SLICE_RATIO_APPLY_DELAY_MS: int = 350
SLICE_REBUILD_SETTLE_TICKS: int = 8
SLICE_REBUILD_MAX_WAIT_S: float = 12.0
SLICE_REBUILD_POLL_S: float = 0.02
SETTLE_TIME: float = 1.0
# -- System Resources --
MAX_WORKER: float = 0.8
# -- Save Settings --
SAVE_EXT: str = 'mp4'
SAVE_PNG_QUALITY: int = -1
SAVE_JPG_QUALITY: int = 80
SAVE_ENCODE_WORKERS: int = get_worker_count(MAX_WORKER)
SAVE_WITH_OVERLAY: bool = True
MUTE_ON_SAVE: bool = False
SAVE_WITH_POPUP: bool = True
MENU_CAPTURE_PUMP_MS: int = 33
AVOID_NAME_COLLISION: bool = True
ABBREVIATE_OUTPUT_FILENAME: bool = True
# -- Edit Undo/Redo --
UNDO_LIMIT: int = 100
# -- Performance / Cache --
PRELOAD_BAR_TITLE_LEN: int = 23
PRELOAD_BAR_LEN: int = 20
RAM_AVAIL_FALLBACK_GB: int = 4
LOAD_PROGRESS_DECODE: float = 0.35
CACHE_HASH_CHUNK_BYTES: int = 1048576
PRELOAD_WORKERS: int = get_worker_count(MAX_WORKER)
SEQ_PRELOAD_WORKERS: int = 4
GPU_AHEAD: int = compute_gpu_ahead()
CHAIN_GPU_AHEAD: int = 99
RANDOM_GPU_AHEAD: int = 45
RANDOM_JUMP_PREWARM: bool = True
RANDOM_JUMP_WARM_AHEAD: int = 30
RANDOM_JUMP_MAX_WAIT_S: float = 0.35
RANDOM_JUMP_POLL_S: float = 0.1
GPU_DEFRAG_THRESHOLD_MB: int = 1536
CPU_SPLAT_CACHE_RAM_FRACTION: float = 0.35
JITTER_GPU_AHEAD: int = 8
# -- Disk Cache (.npz) SH Mode --
CACHING_METHOD: str = 'dc'
CACHE_FLUSH_TIMEOUT: float = 8.0
# -- Shutdown Blink Notice --
SHUTDOWN_BLINK_MESSAGE: str = 'SHUTDOWN IN PROGRESS... PLEASE WAIT...'
SHUTDOWN_BLINK_INTERVAL: float = 0.25
SHUTDOWN_BLINK_COLOR: str = 'green'
SHUTDOWN_BLINK_JOIN_TIMEOUT: float = 1.0
# -- Sequence Cache --
SEQUENCE_CACHE: bool = True
# -- Playback --
PLAYBACK_FPS: int = 30
AUTO_START: bool = True
PLAYBACK_MODE: str = 'chain'
PLAYBACK_MAX_CATCHUP: int = 1
BUFFER_FRAMES_RATIO: float = 0.15
