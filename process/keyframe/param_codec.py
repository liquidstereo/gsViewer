from typing import Callable

def make_param_codec(
    param_keys: tuple, int_keys: tuple = (),
) -> Callable[[dict], dict]:
    int_set = set(int_keys)

    def codec(src: dict) -> dict:
        out = {k: (int(src[k]) if k in int_set else float(src[k]))
               for k in param_keys}
        out['label'] = src.get('label', '')
        out['duration'] = int(src.get('duration', 0) or 0)
        return out

    return codec
