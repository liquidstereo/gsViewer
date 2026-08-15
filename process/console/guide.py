from process.console.expr import rand_namespace

_VAR_DESC = {
    'audio_low': 'low-band audio magnitude average (0~1)',
    'audio_mid': 'mid-band audio magnitude average (0~1)',
    'audio_high': 'high-band audio magnitude average (0~1)',
    't': 'elapsed playback seconds (raw, no scale)',
    'frame': 'playback frame counter (raw tick)',
    'PI': 'circle constant 3.14159...',
}
_VAR_SUFFIX_DESC = {
    'amount': 'random strength multiplier',
    'seed': 'RNG seed (fixed = reproducible)',
    'reroll': 'reroll counter (bump to re-sample)',
    'mode': 'distribution: uniform or gaussian',
    'gain': 'delta scale on top of amount',
    'threshold': 'gate lower bound (0~1)',
    'softness': 'gate soft width (0 = hard)',
    'interval': 'seconds sharing one value',
}

_GUIDE_BODY = '''The Script Console edits a plugin's settings live. Type a value or an
expression after a "KEY", and the scene updates as you type. Nothing is
written to disk until you use File > Save As.

1. BASIC FORMAT

Each line is:   "KEY": value

- value can be a number (0.5), text ("curl"), a list ([1, 0, 0]),
  or an expression such as (audio_low * 5).
- Quotes around a value are OPTIONAL. Both of these work:
      "DEFAULT_GAIN": 0.35 + wiggle(2)
      "DEFAULT_GAIN": "0.35 + wiggle(2)"
- Edit only the value on the right. Do not rename the "KEY".

2. MATH

Expressions use only  + - * /  and parentheses ( ).
NOT supported: if, comparisons (>=, ==), % (modulo), ** (power).
Use the functions in section 4 for ramps, limits and conditions.

3. TIME

  t      = elapsed playback seconds (0 when stopped or at the start)
  frame  = playback frame counter

Example - grow from 0 to 100 over the first 2 seconds, then hold:
      "SOME_CONST": linear(t, 0, 2, 0, 100)

4. FUNCTIONS

Remap and limit:
  clamp(v, lo, hi)            keep v inside [lo, hi]
  linear(x, x0, x1, v0, v1)   map x in [x0,x1] onto [v0,v1] (clamped)
  ease / ease_in / ease_out   same as linear, but smoothed
  smoothstep(e0, e1, x)       smooth 0..1 ramp between e0 and e1

Conditions (there is no "if" - build it from step + pick):
  step(edge, x)     = 1 if x >= edge, else 0
  pick(cond, a, b)  = a if cond is non-zero, else b

  Example - "if t >= 10 then 10 else 5":
      "DEFAULT_NOISE_THRESHOLD": pick(step(10, t), 10, 5)

Plain math:
  sin cos sqrt abs min max pow int round floor ceil  (all return floats)

Animation (each appears only when its source is loaded):
  random(x)                  static per-attribute random in [-x, x]
  wiggle(x)                  per-frame animated random * x
  time(x)                    playback-time ramp
  spring(x[, freq, damp])    x chased with physical overshoot / settle

5. AUDIO   (available when you start with:  -a <audio file>)

  audio_low / audio_mid / audio_high   band-average magnitude (0~1)
  audio_band0 ... audio_bandN          per-band magnitude (0~1)

Example - drive a value from the audio:
      "DEFAULT_NOISE_THRESHOLD": (audio_low * 5) + (audio_band5 * 1.6)

6. YOUR OWN VARIABLES

Any name that is NOT a key in this settings file becomes a variable.
Define it once, then reuse it anywhere (order does not matter):
      "PULSE": (audio_low * 5) + (audio_band7 * 2.4)
      "DEFAULT_NOISE_THRESHOLD": PULSE
      "DEFAULT_NOISE_GAIN": PULSE * 0.5

7. REGION TRANSFORM   (box / region plugins)

  {PREFIX}_POSITION / {PREFIX}_SCALE / {PREFIX}_ROTATE set the region
  box straight from the console, in viewer (gizmo) coordinates. PREFIX
  is the plugin name in capitals, e.g. NOISE_POSITION. Each is [x, y, z].
'''

def console_guide_text(window, title_name: str = '') -> str:
    title = ('SCRIPT CONSOLE - How to Use ' + title_name if title_name
             else 'SCRIPT CONSOLE - SCRIPTING GUIDE')
    lines = [title, '=' * len(title), '', _GUIDE_BODY.rstrip(), '', '',
             '8. VARIABLES AVAILABLE RIGHT NOW  (this session)', '']
    ns = rand_namespace(window)
    scalars = sorted(n for n, v in ns.items() if not callable(v))
    if not scalars:
        lines.append('  (none yet - load a plugin or start with -a audio)')
    for name in scalars:
        desc = _describe_var(name)
        lines.append(f'  - {name}: {desc}' if desc else f'  - {name}')
    return '\n'.join(lines) + '\n'

def _describe_var(name: str) -> str:
    if name in _VAR_DESC:
        return _VAR_DESC[name]
    if name.startswith('audio_band'):
        return 'per-band audio magnitude (0~1)'
    if name.startswith('attr_'):
        return 'active Apply Random target value'
    return _VAR_SUFFIX_DESC.get(name.rsplit('_', 1)[-1], '')
