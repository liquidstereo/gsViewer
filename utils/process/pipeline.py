import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from alive_progress import alive_bar
from configs.settings import PRELOAD_WORKERS
from utils.process.formats import (
    _CODEC_SUFFIX,
    _DECODERS,
    _ENCODERS,
    _detect_format,
    collect_files,
    resolve_output_file,
    strip_ext,
)

logger = logging.getLogger(__name__)

def _convert_one(in_file: Path, out_file: Path, fmt: str) -> bool:
    try:
        t0 = time.perf_counter()
        buf = _DECODERS[_detect_format(in_file)](in_file)
        _ENCODERS[fmt](buf, out_file)
        logger.debug(
            'Converted %s -> %s (%.3fs)',
            in_file.name, out_file.name, time.perf_counter() - t0,
        )
        return True
    except Exception as e:
        logger.error('Failed %s: %s', in_file.name, e)
        return False

def convert_dir(
    input_dir: Path, out_dir: Path, fmt: str
) -> list[Path]:
    files = collect_files(input_dir)
    if not files:
        raise ValueError(f'No supported files found in: {input_dir}')

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = _CODEC_SUFFIX[fmt]
    total = len(files)
    ok = 0

    logger.info(
        'Batch convert: %d files %s -> %s [codec=%s, workers=%d]',
        total, input_dir.name, out_dir.name, fmt, PRELOAD_WORKERS,
    )
    t0 = time.perf_counter()
    with alive_bar(
        total,
        spinner=None,
        title=f'CONVERTING TO {fmt.upper()}...',
        title_length=21,
        length=20,
        dual_line=False,
        stats=True,
        elapsed=True,
        manual=False,
        enrich_print=False,
    ) as bar:
        with ThreadPoolExecutor(
            max_workers=PRELOAD_WORKERS,
            thread_name_prefix='Convert',
        ) as executor:
            fut_map = {
                executor.submit(
                    _convert_one,
                    in_file,
                    out_dir / f'{strip_ext(in_file.name)}{suffix}',
                    fmt,
                ): in_file
                for in_file in files
            }
            for fut in as_completed(fut_map):
                if fut.result():
                    ok += 1
                bar()
        bar.title = f'CONVERT TO {fmt.upper()} COMPLETE'

    elapsed = time.perf_counter() - t0
    logger.info(
        'Done: %d/%d converted in %.2fs -> %s',
        ok, total, elapsed, out_dir,
    )
    if ok < total:
        raise RuntimeError(
            f'{total - ok} file(s) failed during conversion'
        )
    return collect_files(out_dir)

def convert_file(
    input_path: Path,
    output_arg: str | None,
    codec: str | None,
) -> tuple[Path, str]:
    out_path, out_fmt = resolve_output_file(
        input_path, output_arg, codec
    )
    logger.info(
        'Converting %s -> %s [codec=%s]',
        input_path.name, out_path.name, out_fmt,
    )
    t0 = time.perf_counter()
    with alive_bar(
        2,
        spinner=None,

        title=f'CONVERTING TO {out_fmt.upper()}...',
        title_length=21,
        length=20,
        dual_line=False,
        stats=False,
        elapsed=True,
        manual=False,
        enrich_print=False,
    ) as bar:
        buf = _DECODERS[_detect_format(input_path)](input_path)
        bar()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _ENCODERS[out_fmt](buf, out_path)
        bar()

    logger.info(
        'Done: %d gaussians in %.3fs -> %s',
        buf.n_gaussians, time.perf_counter() - t0, out_path,
    )
    return out_path, out_fmt
