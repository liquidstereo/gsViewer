import time

def clamped_wall_dt(
    prev_ts: float | None, dt_max: float,
) -> tuple[float, float]:
    now = time.perf_counter()
    if prev_ts is None:
        return 0.0, now
    return min(now - prev_ts, dt_max), now
