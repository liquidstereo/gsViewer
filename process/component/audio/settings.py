from pathlib import Path

from configs.settings import INPUT_DIR

AUDIO_DIR: Path = INPUT_DIR / 'audio'

AUDIO_AUTO_EXTS: tuple[str, ...] = (
    '.wav', '.aif', '.aiff', '.flac', '.ogg', '.mp3',
)

AUDIO_OUTPUT_DEVICE:    str | None       = 'pulse'
AUDIO_OUTPUT_BLOCKSIZE: int              = 2048
AUDIO_OUTPUT_LATENCY:   str | float | None = None

AUDIO_TARGET_SAMPLE_RATE: int = 44100

AUDIO_STATUS_LATENCY_SEC: float = 0.0

DEFAULT_FFT_WIN: int = 2048
DEFAULT_HOP:     int = 512

AUDIO_FFT_CHUNK_FRAMES: int = 4096

AUDIO_MAX_PRELOAD_CHANNELS: int = 8

ATTR_EXTRA_AUDIO: str = 'audio'

DEFAULT_BANDS: list[tuple[float, float]] = [
    (0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5),
    (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0),
]

DEFAULT_BAND_NAMES: list[str] = [
    'band_0', 'band_1', 'band_2', 'band_3', 'band_4',
    'band_5', 'band_6', 'band_7', 'band_8', 'band_9',
]

AUDIO_SILENCE_DBFS: float = -90.0

AUDIO_DISPLAY_DB_FLOOR: float = -60.0

AUDIO_OVERLAY_MODE: str = 'waveform'

AUDIO_OVERLAY_ACTIVE_DEFAULT: bool = False

AUDIO_ACTIVATE_KEY: str = 'X'

AUDIO_SYNC_DEFAULT: bool = True

AUDIO_MUTE_DEFAULT: bool = False

AUDIO_SECTION_ORDER: int = 20

AUDIO_OVERLAY_BOX_ROWS:      int   = 4
AUDIO_OVERLAY_PAD_RATIO:     float = 0.10
AUDIO_OVERLAY_BAR_GAP_RATIO: float = 0.25

AUDIO_BAND_VALUE_FMT:        str   = '{:.3f}'

AUDIO_BAND_NUM:              bool  = True

AUDIO_BAND_NUM_FMT:          str   = '{:02d} . '

AUDIO_BAND_METER_VMAX:       float = 1.0

AUDIO_WAVE_WINDOW_SEC: float = 0.05
AUDIO_WAVE_LINE_W:     float = 1.0
AUDIO_WAVE_AMP_RATIO:  float = 0.9

WAVEFORM_GAIN:         float = 3.0

PLAYBACK_STOP_POLL_S:  float = 0.05
