import logging

logger = logging.getLogger(__name__)

def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

class TimeConsoleContributor:

    console_key: str = 'time'

    def __init__(self, component) -> None:
        self.component = component

    def snapshot(self) -> dict:
        return self.component.snapshot()

    def value_hints(self) -> dict:
        return {
            'scale': 'ramp rate per second for time(x)',
            'mode': 'linear',
        }

    def apply(self, values: dict) -> None:
        if not isinstance(values, dict):
            return
        c = self.component
        if _is_number(values.get('scale')):
            c.set_scale(float(values['scale']))
        mode = values.get('mode')
        if isinstance(mode, str):
            c.set_mode(mode)

def register_time_console(window) -> None:
    contributors = getattr(window, '_console_contributors', None)
    if contributors is None:
        contributors = []
        window._console_contributors = contributors
    contributors.append(TimeConsoleContributor(window._time_component))
