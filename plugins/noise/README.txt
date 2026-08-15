NOISE PLUGIN  (Reveal with Opacity/Size Ramp)
=======================================
Scatter the splat points inside the region_volume box with realistic,
divergence-free noise (self-contained backend in plugins/noise/noises/).
While active the scattered points flow continuously like turbulence
(the curl field advances over time, NOISE_SPEED).

A spatial ramp (linear / spherical / box) plus a keyframable threshold
makes the scattered points return to their original position
progressively, with opacity and splat size gated by the reveal
progress: threshold 0 = fully scattered/flowing, 1 = fully restored.
A separate Size Var attribute distributes splat size by region center
distance (center ~1.0, edge ~EDGE_MIN), independent of the threshold.

Activate:
    python gsviewer.py -i <input> -p noise

Keys (plugin-specific):
    X         toggle noise on/off
    T         cycle noise type (curl/perlin/turbulence/fractal/worley/simplex)
    O / I     threshold up / down (hold to sweep scatter<->restore)

Panel: 'Falloff' selects the spatial mapping (linear/spherical/box;
x-axis = rv, center 0 -> edge 1). 'Intensity' is the editable transfer
curve. 'Opacity' / 'Scale' curves multiply opacity / splat size by rv
inside the region map (flat y=1.0 default = original preserved). The
spatial ramp logic is the shared common module plugins/region_volume/
ramp/ (field/curve/apply/state/specs), reused by liquify/audio_distortion.

Intensity transfer curve (attribute_overlay, KIND_CURVE):
    Click the 'Intensity' header to expand/collapse the curve box
    (collapsed by default). reveal = 1 - curve(rv).
    - Drag a control point to reshape (real time). Endpoints move
      vertically only; inner points keep x order.
    - Right-click on a point: pick tangent (Linear / Easy Ease /
      Easy In / Easy Out / Flat) or Remove Point (inner points only).
    - Right-click on empty curve area: Add Point (at cursor).
    - Starts with 3 points (Easy Ease). threshold O/I pans the
      curve: 0.5 = curve as-is (every point active), 0 = all scattered,
      1 = all restored (keyframable).
    Curves persist in curves.json and are also captured by Save As /
    Apply JSON Settings (preset 'curves' section).
    Clickable panel elements highlight (#FF5050) on hover. While the
    cursor is over the panel, the region_volume behind it is not
    hover-selectable (clicks/hover are consumed by the panel).
    The curve component is the reusable body module curve_model.CurveState
    (KIND_CURVE) - any attribute can host its own ramp curve.

Animation workflow:
    1. H show region, W/E/R place it over the model.
    2. X to activate. Press I until threshold=0.00 (fully scattered).
    3. Shift+A to add keyframe 'scatter'.
    4. Press O until threshold=1.00 (fully restored).
    5. Shift+A to add keyframe 'restore'.
    6. Shift+PageUp / PageDown to play the interpolation.

Keys (region_volume common - plugins/region_volume/settings.py):
    H                  Toggle region wireframe + face overlay
    L                  Lock region transform (disable tools)
    Shift+1-9          Select active box (multi-box, e.g. -p 'crop, noise')
    Shift+R            Reset region transform + clear effect state
    W / E / R          Translate / Rotate / Scale region_volume tool
    Y                  Cycle region shape (cube/sphere/cylinder/
                       cone/capsule/torus)
    Shift+A            Add current region state as keyframe
    Shift+PageUp/Down  Prev / Next keyframe (EasyEase interpolation)
    Shift+D            Remove last keyframe
    Shift+Delete       Clear all keyframes

Dependencies:
    plugins/region_volume    (auto-resolved via REQUIRES_PLUGINS)
    (noise backend is self-contained in plugins/noise/noises/ — no
     dependency on other effect plugins)

Conflicts:
    plugins/particle         (X key shared)
    region_volume siblings (crop/fluid_explosion/liquify) coexist via the
    selection-aware key router (Shift+1~9 main row / click to select a box).

Settings (plugins/noise/settings.py):
    VOLUME_SHAPE        - region shape ('cube' / 'sphere' / 'cylinder')
    STARTUP_VISIBILITY  - show region box at start
    STARTUP_ACTIVE      - apply noise at start
    NOISE_REGION_CENTER / _SIZE / _SOFTNESS
    NOISE_NOISE_TYPE / _GAIN / _FREQ / _SPEED / _OCTAVES
    NOISE_RAMP_SHAPE / _RAMP_AXIS / _WIDTH / _MIN_OPACITY / _SIZE_MIN
    NOISE_SIZE_VAR / _SIZE_VAR_EDGE_MIN   (size variability)
    NOISE_CURVE_LUT_N / _CURVE_HANDLES    (ramp transfer curve)
    NOISE_STARTUP_THRESHOLD
    NOISE_KEY_TRIGGER / _KEY_CYCLE_TYPE
    NOISE_KEY_THRESHOLD_UP / _KEY_THRESHOLD_DOWN   (O / I)

Region / keyframe JSON storage:
    json/<input>/noise/region.json
    json/<input>/noise/keyframes.json
    json/<input>/noise/curves.json
