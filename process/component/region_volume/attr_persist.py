import logging

from process.widget.overlays.attr_spec import (
    KIND_BOOL, KIND_CURVE, KIND_ENUM, KIND_FLOAT, KIND_INT,
)

logger = logging.getLogger(__name__)

_VALUE_KINDS = (KIND_BOOL, KIND_ENUM, KIND_FLOAT, KIND_INT)

_EXCLUDE_LABELS = frozenset({'Shape'})

def _value_specs(specs) -> list:
    out = []
    for sp in specs or []:
        if sp.kind not in _VALUE_KINDS or sp.label in _EXCLUDE_LABELS:
            continue
        if sp.get is not None and sp.set is not None:
            out.append(sp)
    return out

def _coerce(value):
    item = getattr(value, 'item', None)
    return item() if callable(item) else value

def snapshot(specs) -> dict:
    return {sp.label: _coerce(sp.get()) for sp in _value_specs(specs)}

def defaults(specs) -> dict:
    out = {}
    for sp in _value_specs(specs):
        if sp.default is not None:
            out[sp.label] = _coerce(sp.default)
    return out

def curve_defaults(specs) -> dict:
    out = {}
    for sp in specs or []:
        if sp.kind == KIND_CURVE and sp.default is not None:
            out[sp.label.lower()] = [
                [float(p[0]), float(p[1]), p[2]] for p in sp.default
            ]
    return out

def restore(specs, data: dict) -> None:
    for sp in _value_specs(specs):
        if sp.label not in data:
            continue
        try:
            sp.set(data[sp.label])
        except (ValueError, TypeError) as e:
            logger.warning('Attr restore skipped (%s): %s', sp.label, e)
