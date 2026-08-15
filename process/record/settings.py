FFMPEG_BIN = 'ffmpeg'

VIDEO_EXTS = ('mp4', 'mov')

FALLBACK_IMG_EXT = 'png'

INPUT_PIX_FMT = 'rgb24'

DEFAULT_SAVE_FPS = 30

VIDEO_CODEC = 'auto'

NVENC_CODEC = 'h264_nvenc'
SW_CODEC = 'libx264'

CODEC_ARGS = {
    'h264_nvenc': [
        '-preset', 'p5', '-rc', 'vbr', '-cq', '21', '-b:v', '0',
        '-bf', '0', '-pix_fmt', 'yuv420p',
    ],
    'hevc_nvenc': [
        '-preset', 'p5', '-rc', 'vbr', '-cq', '23', '-b:v', '0',
        '-bf', '0', '-pix_fmt', 'yuv420p',
    ],
    'libx264': [
        '-preset', 'veryfast', '-crf', '20', '-bf', '0',
        '-pix_fmt', 'yuv420p',
    ],
    'prores_ks': ['-profile:v', '3'],
    'ffv1': ['-level', '3'],
}

QUALITY_PRESETS = ('low', 'medium', 'high', 'raw')

QUALITY_FORCE_CODEC = 'libx264'

VIDEO_PRESET_MAP = {
    'low': 'ultrafast',
    'medium': 'medium',
    'high': 'slow',
    'raw': 'veryslow',
}

PNG_QUALITY_MAP = {
    'low': 0,
    'medium': 50,
    'high': -1,
    'raw': 100,
}

