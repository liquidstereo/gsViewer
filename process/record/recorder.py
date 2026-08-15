import logging
import subprocess
from pathlib import Path

from process.record.settings import (
    FFMPEG_BIN, INPUT_PIX_FMT, CODEC_ARGS,
)

logger = logging.getLogger(__name__)

class FFmpegRecorder:

    def __init__(
        self, out: Path, w: int, h: int, fps: int, codec: str,
        args_override: list[str] | None = None,
    ) -> None:
        self._out = out
        self._w = w
        self._h = h
        self._fps = fps
        self._codec = codec
        self._args_override = args_override
        self._proc: subprocess.Popen | None = None
        self._frames = 0

    @property
    def frames(self) -> int:
        return self._frames

    def _build_cmd(self) -> list[str]:
        args = (
            self._args_override if self._args_override is not None
            else CODEC_ARGS.get(self._codec, [])
        )
        return [
            FFMPEG_BIN, '-y',
            '-f', 'rawvideo',
            '-pix_fmt', INPUT_PIX_FMT,
            '-s', f'{self._w}x{self._h}',
            '-r', str(self._fps),
            '-i', '-',
            '-an',
            '-c:v', self._codec,
            *args,
            str(self._out),
        ]

    def start(self) -> bool:
        cmd = self._build_cmd()
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, ValueError) as exc:
            logger.error('ffmpeg recorder start failed: %s', exc)
            self._proc = None
            return False
        logger.info(
            'ffmpeg recorder started: %s (%dx%d @%dfps, %s)',
            self._out, self._w, self._h, self._fps, self._codec,
            extra={'overlay': False},
        )
        return True

    def write(self, data: bytes) -> None:
        if self._proc is None or self._proc.stdin is None:
            return
        try:
            self._proc.stdin.write(data)
            self._frames += 1
        except (BrokenPipeError, OSError) as exc:
            logger.error('ffmpeg recorder write failed: %s', exc)
            self._proc = None

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
            proc.wait(timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            logger.error('ffmpeg recorder close failed: %s', exc)
            proc.kill()
        logger.info(
            'ffmpeg recorder closed: %s (%d frames)',
            self._out, self._frames,
            extra={'overlay': False},
        )
