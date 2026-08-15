import logging
import time

from alive_progress import alive_bar
from configs.settings import PRELOAD_BAR_LEN, PRELOAD_BAR_TITLE_LEN

from process.data.buffer import FrameBuffer

logger = logging.getLogger(__name__)

def preload_unified(buffers: list[FrameBuffer]) -> None:
    files_total = sum(len(b._files) for b in buffers)
    if files_total == 0:
        return
    t0 = time.perf_counter()
    title = next(
        (b._preload_title() for b in buffers if b._files),
        'LOADING DATA FILES...',
    )
    with alive_bar(
        files_total,
        spinner=None,
        title=title,
        title_length=PRELOAD_BAR_TITLE_LEN,
        length=PRELOAD_BAR_LEN,
        dual_line=True,
        stats=True,
        elapsed=True,
        manual=False,
        enrich_print=False,
    ) as bar:
        def _tick() -> None:
            bar()
        for buf in buffers:
            buf.preload_external(_tick)
        bar.title = 'FILES LOAD COMPLETE'
    logger.info(
        'RAM preload (unified) complete: %d files / %d inputs in %.1fs',
        files_total, len(buffers), time.perf_counter() - t0,
    )
