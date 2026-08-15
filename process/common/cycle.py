from typing import Sequence, TypeVar

T = TypeVar('T')

def cycle_next(items: Sequence[T], current: T) -> T:
    if not items:
        raise IndexError('cycle_next: empty sequence')
    if current not in items:
        return items[0]
    idx = items.index(current)
    return items[(idx + 1) % len(items)]
