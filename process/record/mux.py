import logging
import os
import subprocess
import tempfile
from pathlib import Path

from process.record.settings import FFMPEG_BIN

logger = logging.getLogger(__name__)

_SR = 44100

def _segment_filter(
    idx: int, ref: str | None, dur: float, start: float = 0.0,
) -> tuple[str, str]:
    label = f'[s{idx}]'
    fmt = f'aformat=sample_rates={_SR}:channel_layouts=stereo'
    if ref is None:
        src = f'anullsrc=r={_SR}:cl=stereo:d={dur:.6f}'
        return f'{src},{fmt}{label}', label
    chain = (
        f'atrim={start:.6f}:{(start + dur):.6f},asetpts=PTS-STARTPTS,'
        f'apad=whole_dur={dur:.6f},{fmt}'
    )
    return f'{ref}{chain}{label}', label

def _build_command(
    video: Path, out: Path, segments: list, script: Path,
) -> list[str]:
    cmd = [FFMPEG_BIN, '-y', '-i', str(video)]

    uses: dict[str, int] = {}
    order: list[str] = []
    for path, *_rest in segments:
        if path is None:
            continue
        key = str(path)
        if key not in uses:
            uses[key] = 0
            order.append(key)
            cmd += ['-i', key]
        uses[key] += 1
    in_idx = {key: i + 1 for i, key in enumerate(order)}
    parts = []
    fan: dict[str, list[str]] = {}
    for key in order:
        idx = in_idx[key]
        n = uses[key]
        if n == 1:
            fan[key] = [f'[{idx}:a]']
            continue
        split = [f'[a{idx}_{k}]' for k in range(n)]
        parts.append(f'[{idx}:a]asplit={n}{"".join(split)}')
        fan[key] = split
    cursor: dict[str, int] = {key: 0 for key in order}
    labels = []
    for i, (path, dur, *rest) in enumerate(segments):

        start = rest[0] if rest else 0.0
        if path is None:
            ref = None
        else:
            key = str(path)
            ref = fan[key][cursor[key]]
            cursor[key] += 1
        part, label = _segment_filter(i, ref, dur, start)
        parts.append(part)
        labels.append(label)
    concat = (
        f'{"".join(labels)}concat=n={len(segments)}:v=0:a=1[aout]'
    )
    filt = ';'.join(parts + [concat])

    script.write_text(filt)
    cmd += [
        '-filter_complex_script', str(script),
        '-map', '0:v', '-map', '[aout]',
        '-c:v', 'copy', '-c:a', 'aac', '-shortest', str(out),
    ]
    return cmd

def mux_audio(video_path: Path, segments: list) -> bool:
    if not segments or not video_path.is_file():
        return False

    tmp = video_path.with_name(f'.{video_path.stem}_muxed{video_path.suffix}')
    fd, script_name = tempfile.mkstemp(prefix='gsv_afilter_', suffix='.txt')
    os.close(fd)
    script = Path(script_name)
    cmd = _build_command(video_path, tmp, segments, script)
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
    except Exception as exc:
        logger.error('Audio mux failed to run: %s', exc)
        return False
    finally:
        script.unlink(missing_ok=True)
    if proc.returncode != 0 or not tmp.is_file():
        logger.error(
            'Audio mux ffmpeg error (code=%d): %s',
            proc.returncode, proc.stderr.decode('utf-8', 'ignore')[-500:],
        )
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(video_path)
    logger.info('Audio muxed into %s', video_path.name)
    return True
