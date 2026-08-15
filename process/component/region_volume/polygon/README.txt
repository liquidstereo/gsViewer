Polygon Prism Region (process/component/region_volume/polygon/)
===============================================================

Purpose
-------
A prism region built by extruding an arbitrary polygon drawn on screen
along the camera forward axis (view normal). Unlike fixed shapes such as
cube/sphere, it is used for free-form cropping. Implemented as an
independent subpackage, so every region_volume plugin (crop / noise /
liquify ...) supports it through the shape factory alone.

Activation / workflow
---------------------
1. Show the region (H), then switch Shape to 'polygon' (cycle with Y or
   pick it from the attribute_overlay Shape dropdown).
2. (Recommended) Press F5 for Front View.
3. LMB-click vertices on screen to draw a free polygon.
   Backspace cancels the last vertex.
4. Enter (or Numpad Enter) confirms the polygon and creates the prism
   extruded along the camera forward axis.
5. Use R (Scale tool) to adjust the extrude depth. W/E/R transforms and
   keyframes behave exactly like the shared region_volume keys.
6. Existing crop shortcuts (X toggle / T invert) keep working.

Keys
----
LMB         add vertex
Enter       confirm polygon (create extruded prism)
Backspace   cancel last vertex
W/E/R       Translate / Rotate / Scale (= extrude depth)
others      shared region_volume keys (H, X, Y, Shift+A/D ...)

Dependencies
------------
- process/component/region_volume (RegionSolid / overlay / picking /
  key_router)
- process.transform coordinate contract: exposing _viewmat/_K is enough,
  so the package is reusable independently of the host application.

Settings location
-----------------
Polygon-specific constants (drawing color / keys / initial extrude ratio)
live in settings.py of this directory. Shared shape constants such as
VOLUME_SHAPE_POLYGON live in region_volume/settings.py.

Implementation notes
--------------------
- The mask is view independent: point-in-polygon on the plane basis plus
  |n| <= depth/2 with softness.
- 2D->3D back-projection (numpy) is reprojected with the camera matrix;
  side lines are drawn with QPainter over the GPU readback QImage (the
  same path used by the other shape overlays).
