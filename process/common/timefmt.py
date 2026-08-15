def fmt_mmss_ms(sec: float) -> str:
    total = int(round(max(0.0, sec) * 1000))
    m, rem = divmod(total, 60000)
    s, ms = divmod(rem, 1000)
    return f'{m:02d}:{s:02d}:{ms:03d}'
