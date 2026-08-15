import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from alive_progress import alive_bar
from PIL import Image

from configs.settings import SEQUENCE_DIR
from configs.settings import SEQUENCE_CACHE
from configs.settings import SEQ_PRELOAD_WORKERS
from configs.settings import IGNORE_SEQUENCE_INPUT
from process.common.natural_sort import natural_sorted
from process.common.resource_lookup import resolve_named_resource

logger = logging.getLogger(__name__)

SEQ_IMAGE_EXTS: tuple[str, ...] = ('.png', '.jpg', '.jpeg')

def _load_frame(path: Path) -> np.ndarray | None:
    try:
        return np.array(Image.open(path))
    except Exception:
        return None

def find_sequence_path_candidates(input_name: str) -> Path | None:
    return resolve_named_resource(SEQUENCE_DIR, input_name, SEQ_IMAGE_EXTS)

def _resolve_seq_path(
    seq_arg: str | None,
    input_name: str,
    search_path: Path | None = None,
) -> Path | None:
    if seq_arg:
        p = Path(seq_arg)
        if p.exists():
            return p
        p = SEQUENCE_DIR / seq_arg
        if p.exists():
            return p

        for ext in ('.png', '.jpg', '.jpeg'):
            pf = p.with_suffix(ext)
            if pf.exists():
                return pf
        logger.warning('Sequence path not found: %s', seq_arg)
        return None

    if IGNORE_SEQUENCE_INPUT:
        return None

    if search_path and search_path.is_file():
        for ext in ('.png', '.jpg', '.jpeg'):
            pf = search_path.with_suffix(ext)
            if pf.exists():
                return pf

    candidate = find_sequence_path_candidates(input_name)
    if candidate is not None:
        return candidate
    return None

def collect_sequence_files(
    path: Path,
    rng: str | None = None,
) -> list[Path]:
    if not path.exists():
        raise FileNotFoundError(
            f'Sequence path not found: {path}'
        )

    if path.is_file():
        return [path]

    files = []
    for ext in ('*.png', '*.jpg', '*.jpeg'):
        files.extend(path.glob(ext))

    files = natural_sorted(files)

    if rng is not None:
        start, end = (int(x) for x in rng.split('-'))
        files = files[start:end + 1]
    if not files:
        logger.warning('No image files in: %s', path)
    return files

def _nearest_decoded(results: dict[int, np.ndarray], idx: int, n: int) -> int:
    for j in range(idx - 1, -1, -1):
        if j in results:
            return j
    for j in range(idx + 1, n):
        if j in results:
            return j
    return -1

def _fill_missing_frames(
    results: dict[int, np.ndarray], files: list[Path]
) -> list[np.ndarray]:

    n = len(files)
    if not results:
        return []
    frames: list[np.ndarray] = []
    missing: list[int] = []
    for i in range(n):
        frame = results.get(i)
        if frame is None:
            missing.append(i)
            frame = results[_nearest_decoded(results, i, n)].copy()
        frames.append(frame)
    if missing:
        logger.error(
            'Sequence decode failed for %d/%d frames, substituted to '
            'preserve frame index (first: %s)',
            len(missing), n, files[missing[0]].name,
        )
    return frames

def load_sequence_to_ram(
    directory_path: Path,
    rng: str | None = None,
) -> list[np.ndarray]:
    files = collect_sequence_files(directory_path, rng)
    if not files:
        return []

    n = len(files)
    is_single = n == 1
    results: dict[int, np.ndarray] = {}
    with alive_bar(
        None if is_single else n,
        spinner=None,
        title='SEQUENCE CACHE BUILDING...',
        title_length=23,
        length=20,
        dual_line=True,
        manual=is_single,
        stats=not is_single,
        elapsed=True,
        enrich_print=False,
    ) as bar:
        with ThreadPoolExecutor(
            max_workers=SEQ_PRELOAD_WORKERS
        ) as executor:
            futures = {
                executor.submit(_load_frame, f): i
                for i, f in enumerate(files)
            }
            for fut in as_completed(futures):
                idx = futures[fut]
                frame = fut.result()
                if frame is None:
                    logger.warning(
                        'Failed to load frame: %s', files[idx]
                    )
                else:
                    results[idx] = frame
                bar(1.0) if is_single else bar()
            bar.title = 'SEQUENCE CACHE COMPLETE'

    return _fill_missing_frames(results, files)

def init_seq_player(
    seq_arg: str | None,
    input_name: str = '',
    rng: str | None = None,
    use_cache: bool = SEQUENCE_CACHE,
    search_path: Path | None = None,
) -> 'SequencePlayer | None':
    from process.sequence.player import SequencePlayer
    p = _resolve_seq_path(seq_arg, input_name, search_path=search_path)
    if p is None:
        return None
    if use_cache:
        t0 = time.perf_counter()
        frames = load_sequence_to_ram(p, rng=rng)
        elapsed = time.perf_counter() - t0
        if not frames:
            return None
        logger.info(
            'Sequence RAM cache: %d frames in %.3f s from %s',
            len(frames), elapsed, p,
        )
        return SequencePlayer(frames=frames)
    else:
        files = collect_sequence_files(p, rng=rng)
        if not files:
            return None
        logger.info(
            'Sequence on-demand: %d frames registered (no preload) from %s',
            len(files), p,
        )
        return SequencePlayer(files=files)
