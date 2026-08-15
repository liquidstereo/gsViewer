import logging

logger = logging.getLogger(__name__)

def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

class SpringConsoleContributor:

    console_key: str = 'spring'

    def __init__(self, component) -> None:
        self.component = component

    def snapshot(self) -> dict:
        return self.component.snapshot()

    def value_hints(self) -> dict:
        return {
            'freq': 'spring(x) natural frequency in Hz (0.01 ~ 20.0)',
            'damping': '1.0 = no overshoot, lower = bouncier (0.0 ~ 4.0)',
        }

    def apply(self, values: dict) -> None:
        if not isinstance(values, dict):
            return
        c = self.component
        before = (c.freq, c.damping)
        if _is_number(values.get('freq')):
            c.set_freq(float(values['freq']))
        if _is_number(values.get('damping')):
            c.set_damping(float(values['damping']))
        if (c.freq, c.damping) != before:
            c.states.clear()

def register_spring_console(window) -> None:
    contributors = getattr(window, '_console_contributors', None)
    if contributors is None:
        contributors = []
        window._console_contributors = contributors
    contributors.append(SpringConsoleContributor(window._spring_component))
