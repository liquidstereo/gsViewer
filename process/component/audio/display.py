def display_label(window, fallback: str) -> str:
    source = getattr(window, '_audio_display_name', None)
    if source is None:
        return fallback
    name = source()
    return name if name else fallback
