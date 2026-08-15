import json
from decimal import Decimal

def fixed_repr(value: float) -> str:
    text = repr(float(value))
    if 'e' not in text and 'E' not in text:
        return text
    if 'inf' in text or 'nan' in text:
        return text
    out = format(Decimal(text), 'f')
    if '.' not in out:
        out += '.0'
    return out

class _FixedEncoder(json.JSONEncoder):

    def iterencode(self, o, _one_shot: bool = False):
        markers = {} if self.check_circular else None
        if self.ensure_ascii:
            encoder = json.encoder.encode_basestring_ascii
        else:
            encoder = json.encoder.encode_basestring
        allow_nan = self.allow_nan

        def floatstr(value: float) -> str:
            if value != value:
                text = 'NaN'
            elif value == float('inf'):
                text = 'Infinity'
            elif value == float('-inf'):
                text = '-Infinity'
            else:
                return fixed_repr(value)
            if not allow_nan:
                raise ValueError(
                    'Out of range float values are not JSON '
                    f'compliant: {value!r}')
            return text

        iterencode = json.encoder._make_iterencode(
            markers, self.default, encoder, self.indent, floatstr,
            self.key_separator, self.item_separator, self.sort_keys,
            self.skipkeys, _one_shot,
        )
        return iterencode(o, 0)

def dumps_fixed(data: object, **kwargs) -> str:
    kwargs.pop('cls', None)
    return json.dumps(data, cls=_FixedEncoder, **kwargs)
