import logging
from collections import deque

logger = logging.getLogger(__name__)

_RING = 20000

_STAGES = ('fetch', 'proc', 'gpu', 'raster', 'postfx', 'readback',
           'tail', 'save', 'total')

class PerfCollector:

    def __init__(self) -> None:
        self.stages: dict = {s: deque(maxlen=_RING) for s in _STAGES}

    def push(self, **stage_ms: float) -> None:
        for name, value in stage_ms.items():
            buf = self.stages.get(name)
            if buf is not None and value is not None:
                buf.append(float(value))

def _collector(window) -> PerfCollector:
    coll = getattr(window, '_perf', None)
    if coll is None:
        coll = PerfCollector()
        window._perf = coll
    return coll

def perf_push(window, **stage_ms: float) -> None:
    _collector(window).push(**stage_ms)

def _percentile(sorted_vals: list, q: float) -> float:

    if not sorted_vals:
        return 0.0
    idx = int(q * (len(sorted_vals) - 1) + 0.5)
    return sorted_vals[min(len(sorted_vals) - 1, idx)]

def _stat(vals) -> dict:

    s = sorted(vals)
    n = len(s)
    avg = sum(s) / n
    var = sum((x - avg) ** 2 for x in s) / n
    return {
        'n': n, 'avg': avg, 'min': s[0], 'max': s[-1],
        'p99': _percentile(s, 0.99), 'p999': _percentile(s, 0.999),
        'std': var ** 0.5,
    }

def _format_report(coll: PerfCollector) -> str | None:
    total = coll.stages.get('total')
    if not total:
        return None
    tot = _stat(total)
    fps = 1000.0 / tot['avg'] if tot['avg'] > 0 else 0.0
    lines = [
        '',
        'PERF PROFILE (session, -v) -- fetch=set_frame(buf.get+compose), '
        'proc/gpu/tail=render, save=-s capture(grab+encode submit); '
        '%% = share of render total',
        f'  frames={tot["n"]}  render avg={tot["avg"]:.2f}ms  '
        f'FPS~{fps:.1f}',
        '  {:<6} {:>7} {:>7} {:>7} {:>7} {:>7} {:>7} {:>6}'.format(
            'stage', 'avg', 'min', 'max', 'p99', 'p999', 'std', '%'),
    ]
    for name in _STAGES:
        vals = coll.stages.get(name)
        if not vals:
            continue
        st = _stat(vals)
        pct = 100.0 * st['avg'] / tot['avg'] if tot['avg'] > 0 else 0.0
        lines.append(
            '  {:<6} {:>7.2f} {:>7.2f} {:>7.2f} {:>7.2f} {:>7.2f} '
            '{:>7.2f} {:>5.1f}'.format(
                name, st['avg'], st['min'], st['max'], st['p99'],
                st['p999'], st['std'], pct))
    return '\n'.join(lines)

def fps_tick(window, dt_ms: float) -> None:
    buf = getattr(window, '_fps_ring', None)
    if buf is None:
        buf = deque(maxlen=_RING)
        window._fps_ring = buf
    buf.append(dt_ms)

def fps_report(window) -> None:
    buf = getattr(window, '_fps_ring', None)
    if not buf:
        return
    st = _stat(buf)
    avg = st['avg']
    p99 = st['p99']
    logger.info(
        'PERF SESSION frames=%d measured=%.1fs avg_fps=%.2f '
        'low1_fps=%.2f frame_avg=%.2fms min=%.2fms max=%.2fms '
        'p99=%.2fms std=%.2fms',
        st['n'], sum(buf) / 1000.0,
        (1000.0 / avg) if avg > 0 else 0.0,
        (1000.0 / p99) if p99 > 0 else 0.0,
        avg, st['min'], st['max'], p99, st['std'],
    )

def perf_report(window) -> None:
    coll = getattr(window, '_perf', None)
    if coll is None:
        return
    text = _format_report(coll)
    if text is None:
        return

    logger.info('%s', text)
