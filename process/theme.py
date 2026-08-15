import logging
import sys

from configs import settings_color as sc
from process.common import complement_hex

logger = logging.getLogger(__name__)

_THEMES = ('Bright', 'Dark')
_state = {'theme': sc.THEME}

_CONSUMER_PREFIXES = ('process.', 'plugins.')

_REFRESH_HOOK = '_theme_refresh'

def _derive_palette(theme: str) -> dict[str, str]:

    p = sc._BRIGHT if theme == 'Bright' else sc._DARK
    bound = p['BOUND']
    ovtxt = p['OVTXT']
    return {
        'BACKGROUND_COLOR': p['BG'],
        'BOUNDING_COLOR': bound,
        'BBOX_COLOR': bound,
        'GRID_COLOR_FLOOR': bound,
        'GRID_COLOR_WALL_L': bound,
        'GRID_COLOR_WALL_B': bound,
        'GRID_AXIS_LABEL_COLOR': bound,
        'GRID_TICK_COLOR': p['TICK'],
        'MODE_POINT_COLOR': complement_hex(p['BG']),
        'OVERLAY_TEXT_COLOR': ovtxt,
        'OBJECT_LIST_HOVER_COLOR': ovtxt,
        'REGION_LIST_HOVER_COLOR': ovtxt,
        'MESSAGE_OVERLAY_TEXT_COLOR': ovtxt,
        'OVERLAY_SHADOW_COLOR': p['SHADOW'],
    }

_THEMED_NAMES = tuple(_derive_palette(_state['theme']).keys())

def iter_consumer_modules() -> list:
    found = []
    for name, mod in list(sys.modules.items()):
        if mod is None or not name.startswith(_CONSUMER_PREFIXES):
            continue
        if any(hasattr(mod, n) for n in _THEMED_NAMES):
            found.append(mod)
    return found

def _run_refresh_hooks() -> None:

    for name, mod in list(sys.modules.items()):
        if mod is None or not name.startswith(_CONSUMER_PREFIXES):
            continue
        hook = getattr(mod, _REFRESH_HOOK, None)
        if callable(hook):
            hook()

def apply_theme(window, theme: str) -> None:
    derived = _derive_palette(theme)
    sc.__dict__.update(derived)
    for mod in iter_consumer_modules():
        for name in _THEMED_NAMES:
            if hasattr(mod, name):
                setattr(mod, name, derived[name])
    _run_refresh_hooks()
    _state['theme'] = theme
    window._render_current()
    window._widget.update()
    logger.info('Color theme -> %s', theme)

def cycle_theme(window) -> None:
    i = _THEMES.index(_state['theme'])
    apply_theme(window, _THEMES[(i + 1) % len(_THEMES)])
