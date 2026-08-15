import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer

logger = logging.getLogger(__name__)

class SequencePlayer:

    def __init__(
        self,
        frames: list[np.ndarray] | None = None,
        files: list[Path] | None = None,
        opacity: float = 1.0,
    ) -> None:
        self._frames = frames
        self._files = files
        self.total_frames: int = (
            len(frames) if frames is not None else len(files or [])
        )
        self.current_idx: int = 0
        self.opacity: float = float(opacity)
        self._timer: QTimer | None = None

    def get_cached_frame(self, idx: int) -> np.ndarray:
        i = idx % self.total_frames
        if self._frames is not None:
            return self._frames[i]
        t0 = time.perf_counter()
        frame = np.array(Image.open(self._files[i]))
        logger.debug(
            'Sequence on-demand frame %d: %.1f ms',
            i, (time.perf_counter() - t0) * 1000,
        )
        return frame

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
