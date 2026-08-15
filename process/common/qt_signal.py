from typing import Callable

def connect_triggered(action, slot: Callable[[], None]) -> None:
    action.triggered.connect(lambda *_, s=slot: s())
