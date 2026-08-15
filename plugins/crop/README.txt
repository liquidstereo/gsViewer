CROP PLUGIN
=================
Show only the splat points inside the region_volume box and hide the
rest. The opacity of points outside the region is forced to 0, so the
visible result is cropped to the box. Press X to toggle crop on/off and
T to invert (keep the outside instead of the inside). Move/scale/rotate
the box with W/E/R to choose the crop region.

Activate:
    python gsviewer.py -i <input> -p crop

Input support:
    Works on 3DGS input and on pure point cloud .ply input (GL_POINTS
    render path). POINTCLOUD_SUPPORTED = True in settings.py declares
    this. On point cloud input the crop edge is hard: GL_POINTS has no
    per-point alpha, so points are dropped below GLPOINTS_OPACITY_MIN
    (configs/settings_glpoints.py) instead of fading.

Keys (plugin-specific):
    X         toggle crop on/off (show region only)
    T         invert (keep inside <-> keep outside)

Keys (region_volume common - plugins/region_volume/settings.py):
    H                  Toggle region wireframe + face overlay
    L                  Lock region transform (disable tools)
    Shift+1-9          Select active box (multi-box, e.g. -p 'crop, noise')
    Shift+R            Reset region transform + clear crop state
    W / E / R          Translate / Rotate / Scale region_volume tool
    Y                  Cycle region shape (cube/sphere/cylinder/
                       cone/capsule/torus)
    Shift+A            Add current region state as keyframe
    Shift+PageUp/Down  Prev / Next keyframe (EasyEase interpolation)
    Shift+D            Remove last keyframe
    Shift+Delete       Clear all keyframes

Dependencies:
    plugins/region_volume (auto-resolved via REQUIRES_PLUGINS)

Conflicts:
    plugins/particle         (X key shared)
    plugins/fluid_explosion  (X key shared)
    plugins/liquify          (X key shared)

Settings (plugins/crop/settings.py):
    VOLUME_SHAPE                  - region shape (cube / sphere / cylinder)
    STARTUP_VISIBILITY            - show region box at start
    STARTUP_ACTIVE                - apply crop at start
    STARTUP_CROP_REGION_CENTER / STARTUP_CROP_REGION_SIZE
    DEFAULT_VISIBILITY / DEFAULT_ACTIVE  - panel/console editable toggles
    DEFAULT_CROP_INVERT           - Mode: keep outside instead of inside
    DEFAULT_CROP_REGION_SOFTNESS  - region boundary softness
    CROP_KEY_TRIGGER / CROP_KEY_INVERT

Region / keyframe JSON storage:
    json/<input>/crop/region.json
    json/<input>/crop/keyframes.json
    json/<input>/crop/curves.json
