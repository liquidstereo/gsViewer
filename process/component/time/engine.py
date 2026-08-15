def time_eval(component, x: float, tick: int) -> float:
    fps = float(getattr(component, 'fps', 0.0)) or 1.0
    seconds = float(tick) / fps
    return seconds * float(component.scale) * float(x)
