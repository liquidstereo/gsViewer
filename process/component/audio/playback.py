import logging
import os
import time

import numpy as np

from process.component.audio.alsa_silencer import install_alsa_silencer
from process.component.audio.settings import (
    AUDIO_OUTPUT_DEVICE, AUDIO_OUTPUT_BLOCKSIZE, AUDIO_OUTPUT_LATENCY,
    PLAYBACK_STOP_POLL_S,
)

logger = logging.getLogger(__name__)

class AudioPlayback:

    def __init__(self, mono: np.ndarray, sample_rate: int) -> None:
        install_alsa_silencer()
        self._raw: np.ndarray = mono
        self.sample_rate: int = int(sample_rate)
        self._stream = None
        self.cursor: int = 0
        self.paused: bool = False
        self.playing: bool = False
        self.muted: bool = False

    @property
    def num_samples(self) -> int:
        return int(len(self._raw))

    @property
    def output_latency(self) -> float:
        if self._stream is None:
            return 0.0
        return float(getattr(self._stream, 'latency', 0.0) or 0.0)

    def swap_source(self, mono: np.ndarray) -> bool:
        if len(mono) != len(self._raw):
            logger.error(
                'Audio source swap rejected: length %d != current %d',
                len(mono), len(self._raw),
            )
            return False

        self._raw = mono
        return True

    def _callback(self, outdata, frames, time_info, status) -> None:
        n = len(self._raw)
        if self.paused or n == 0:

            outdata.fill(0.0)
            return
        c = self.cursor

        if self.muted:

            outdata.fill(0.0)
        else:
            end = c + frames
            if end <= n:
                outdata[:, 0] = self._raw[c:end]
            else:
                k = n - c
                outdata[:k, 0] = self._raw[c:]
                outdata[k:, 0] = self._raw[:frames - k]
        self.cursor = (c + frames) % n

    def try_play(self) -> None:
        try:
            import sounddevice as sd
            self._stream = self._open_stream(sd)
            self._stream.start()
            self.playing = True
            logger.info('Audio playback started')
            logger.info(
                'Audio output latency=%.4f s (blocksize=%d, sr=%d)',
                self.output_latency, AUDIO_OUTPUT_BLOCKSIZE,
                self.sample_rate,
            )
        except Exception as e:
            logger.warning('Audio playback unavailable: %s', e)

    def _open_stream(self, sd):

        kw = dict(
            samplerate=self.sample_rate, channels=1,
            callback=self._callback, dtype='float32',
        )
        if AUDIO_OUTPUT_BLOCKSIZE:
            kw['blocksize'] = AUDIO_OUTPUT_BLOCKSIZE
        if AUDIO_OUTPUT_LATENCY is not None:
            kw['latency'] = AUDIO_OUTPUT_LATENCY
        if AUDIO_OUTPUT_DEVICE:
            try:
                return sd.OutputStream(device=AUDIO_OUTPUT_DEVICE, **kw)
            except Exception as e:
                logger.warning(
                    'Audio device %r unavailable, fallback default: %s',
                    AUDIO_OUTPUT_DEVICE, e,
                )
        return sd.OutputStream(**kw)

    def pause(self) -> None:
        if not self.playing or self.paused:
            return
        self.paused = True
        logger.info('Audio playback paused')

    def resume(self) -> None:
        if not self.playing or not self.paused:
            return
        self.paused = False
        logger.info('Audio playback resumed')

    def stop(self) -> None:
        if not self.playing:
            return
        try:

            saved = os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 2)
            try:
                if self._stream is not None:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None
                time.sleep(PLAYBACK_STOP_POLL_S)
            finally:
                os.dup2(saved, 2)
                os.close(saved)
                os.close(devnull)
            logger.info('Audio playback stopped')
        except Exception as e:
            logger.warning('Audio stop failed: %s', e)
        finally:
            self.playing = False
            self.paused = False
