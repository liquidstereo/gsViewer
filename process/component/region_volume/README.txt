region_volume -- transform gizmo + box region unified library
============================================================

Unifies the shared behaviour of every plugin that uses a box region_volume
(liquify / audio_distortion / crop / noise / dissect ...) into a single
module: region OBB, wireframe + face overlay, visibility keybinding, reset,
W/E/R tools, and keyframes (Shift+A / Shift+PageUp/Down / Shift+D /
Shift+Delete).

Activation
----------
  python gsviewer.py -i <input> -p liquify
    (liquify depends on region_volume -> auto prepended)
  python gsviewer.py -i <input> -p audio_distortion -a <wav>
    (audio_distortion also depends on region_volume)
  python gsviewer.py -i <input> -p region_volume
    (library only, no visible effect on its own)

Keybindings (settings.py is the single source, shared by all plugins)
---------------------------------------------------------------------
  H                  : toggle box wireframe + face overlay
  L                  : toggle region transform lock (tools disabled)
  Shift+R            : reset box transform + region JSON (restore default)
  W                  : Translate tool
  E                  : Rotate tool
  R                  : Scale tool
  Y                  : cycle region shape
                       (cube/sphere/cylinder/cone/capsule/torus)
  Shift+A            : add current box state as a keyframe
  Shift+PageUp       : ease-interpolate to the previous keyframe
  Shift+PageDown     : ease-interpolate to the next keyframe
  Shift+D            : delete the last keyframe
  Shift+Delete       : delete all keyframes + remove JSON
  Shift+P            : toggle keyframe marker overlay
  Ctrl+Shift+D       : duplicate selected box (copies effect/transform,
                       +X offset, labels renumbered automatically)
  Ctrl+Shift+R       : delete selected box at runtime (REGION LIST included,
                       Ctrl+Z undo, labels renumbered)
  Shift+Numpad +     : increase effect strength_scale (0.1 step)
  Shift+Numpad -     : decrease effect strength_scale (0.1~3.0)
                       * hold to auto-repeat.
                       * only active when the plugin system exposes a
                         strength_scale attribute (e.g. liquify).
                         Plugins such as dissect do not use it.

Shift + drag (free transform)
-----------------------------
  Grabbing any handle or the body performs an axis-free transform per tool.
  Holding Shift draws a yellow square at the gizmo origin to indicate free
  transform mode (all tools).
  W (Translate) : free move on the screen plane (gizmo-free dragging)
  E (Rotate)    : trackball rotation
  R (Scale)     : uniform / constrained resizing

Selection (click)
-----------------
  - Show boxes with H, then LMB-click a box to activate (select) its tool.
    Body-click selection only works when
    configs/settings_transform.MAIN_OBJECT_SELECTION=False
    (when True, main object selection takes priority).

Dependencies
------------
- PySide6
- numpy
- torch (for RegionBox.mask computation)

Settings location
-----------------
process/component/region_volume/settings.py
  - 3-axis colors / picking / size constants (RegionVolumePalette override)
  - REGION default transform/appearance (RegionPalette override)
  - shared keybindings + keyframe animation constants

Usage (adding a new plugin)
---------------------------
1) Subclass ``RegionVolumeBoxController`` in the host plugin class:

    from process.component.region_volume import (
        RegionVolumeBoxController, RegionBox,
    )

    class MyPlugin(RegionVolumeBoxController):
        banner_label = 'MY_FX'
        def __init__(self):
            super().__init__(region=RegionBox(center=..., size=...))

2) Call the standard helper ``attach_box_plugin`` once inside
   ``attach(window)``. It performs register_box_controller +
   frame_processor + key/attribute/help registration in one step:

    from process.component.region_volume import (
        attach_box_plugin, RegionPalette,
    )

    def attach(self, window):
        attach_box_plugin(
            window, self,
            channel='_my_plugin',
            shape=VOLUME_SHAPE,
            register_attributes=register_attributes,
            log_name='My FX',
            region_palette=RegionPalette(color='#ff00ff'),
            with_keyframes=True,
        )

   init_paths resolves region/keyframes/curves JSON paths automatically to
   ``json/<input>/<slug>/{region,keyframes,curves}.json``
   (slug = lowercased overlay_label). The host never sets these paths.

3) Declare ``REQUIRES_PLUGINS=['region_volume']`` in the plugin manifest
   (__init__.py). The dependency is resolved automatically.

Overriding default behaviour
----------------------------
- Colors: RegionVolumePalette(axis_colors=...) / RegionPalette(color=...)
- Custom region overlay (face hover highlight, etc.): pass the
  ``region_painter_override`` callback to attach_box_plugin /
  register_box_controller
- Startup visibility: RegionVolumeBoxController(startup_visibility=False)
- Default tool: RegionVolumeBoxController(tool_default='translate')
