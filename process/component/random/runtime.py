import logging

logger = logging.getLogger(__name__)

def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

class RandomConsoleContributor:

    console_key: str = 'random'

    def __init__(self, component) -> None:
        self.component = component

    def snapshot(self) -> dict:
        return self.component.snapshot()

    def value_hints(self) -> dict:
        return {
            'mode': 'uniform, gaussian',
            'reroll': 'bump +1 to re-sample; same seed+reroll = same value',
            'seed': 'fixed value = reproducible',
            'amount': 'output multiplier for random(x)',
        }

    def apply(self, values: dict) -> None:
        if not isinstance(values, dict):
            return
        c = self.component
        if _is_number(values.get('amount')):
            c.set_amount(float(values['amount']))
        if _is_number(values.get('seed')):
            c.set_seed(float(values['seed']))
        if _is_number(values.get('reroll')):
            c.set_reroll(int(values['reroll']))
        mode = values.get('mode')
        if isinstance(mode, str):
            c.set_mode(mode)

def register_random_console(window) -> None:
    contributors = getattr(window, '_console_contributors', None)
    if contributors is None:
        contributors = []
        window._console_contributors = contributors
    contributors.append(RandomConsoleContributor(window._random_component))
