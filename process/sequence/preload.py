import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from alive_progress import alive_bar

from configs.settings import SEQ_PRELOAD_WORKERS
from process.sequence.loader import (
    _load_frame, _resolve_seq_path, collect_sequence_files,
)

logger = logging.getLogger(__name__)

def _build_frames_cached(
    files: list[Path], bar_tick,
) -> list[np.ndarray]:
    results: dict[int, np.ndarray] = {}
    with ThreadPoolExecutor(max_workers=SEQ_PRELOAD_WORKERS) as executor:
        futures = {
            executor.submit(_load_frame, f): i
            for i, f in enumerate(files)
        }
        for fut in as_completed(futures):
            idx = futures[fut]
            frame = fut.result()
            if frame is None:
                logger.warning('Failed to load frame: %s', files[idx])
            else:
                results[idx] = frame
            bar_tick()
    return [results[i] for i in sorted(results)]

def _resolve_specs(
    specs: list[tuple[str, str | None, str | None, Path | None]],
) -> list[tuple[str, Path, list[Path]]]:
    resolved: list[tuple[str, Path, list[Path]]] = []
    for iid, seq_arg, rng, search_path in specs:
        p = _resolve_seq_path(seq_arg, iid, search_path=search_path)
        if p is None:
            continue
        files = collect_sequence_files(p, rng)
        if not files:
            continue
        resolved.append((iid, p, files))
    return resolved

def init_seq_players_unified(
    specs: list[tuple[str, str | None, str | None, Path | None]],
    use_cache: bool,
) -> dict[str, 'SequencePlayer']:
    from process.sequence.player import SequencePlayer
    resolved = _resolve_specs(specs)
    if not resolved:
        return {}
    if not use_cache:
        players: dict[str, SequencePlayer] = {}
        for iid, path, files in resolved:
            players[iid] = SequencePlayer(files=files)
            logger.info(
                'Sequence on-demand: %d frames from %s',
                len(files), path,
            )
        return players
    files_total = sum(len(f) for _, _, f in resolved)
    t0 = time.perf_counter()
    players: dict[str, SequencePlayer] = {}
    with alive_bar(
        files_total,
        spinner=None,
        title='SEQUENCE CACHE BUILDING...',
        title_length=23,
        length=20,
        dual_line=True,
        manual=False,
        stats=True,
        elapsed=True,
        enrich_print=False,
    ) as bar:
        def _tick() -> None:
            bar()
        for iid, path, files in resolved:
            frames = _build_frames_cached(files, _tick)
            if frames:
                players[iid] = SequencePlayer(frames=frames)
                logger.info(
                    'Sequence RAM cache: %d frames from %s',
                    len(frames), path,
                )
        bar.title = 'SEQUENCE CACHE COMPLETE'
    logger.info(
        'Sequence cache (unified) complete: %d frames / %d seqs in %.1fs',
        files_total, len(resolved), time.perf_counter() - t0,
    )
    return players
