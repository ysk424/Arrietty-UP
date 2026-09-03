"""Validate the authored blend before installing it for a live test."""

from __future__ import annotations

import bpy


def _fail(message: str) -> None:
    raise RuntimeError(f"ARRIETTY_BLEND_VALIDATION_FAIL {message}")


scene = bpy.context.scene
if scene.get("instrument_panel_version") != 3:
    _fail("instrument panel version is not 3")
required_objects = (
    "ArriettyRuntime",
    "InstrumentPanelRoot",
    "Instrument_PFD_Attitude",
    "Instrument_PFD_Sky",
    "Instrument_PFD_Ground",
    "Instrument_PFD_HorizonLine",
    "Instrument_PFD_Ladder",
    "Instrument_PFD_ClipMask",
    "Instrument_PFD_Bezel",
    "Instrument_PFDState",
    "Instrument_PhysicsText",
    "Instrument_DebugText",
)
missing = [name for name in required_objects if scene.objects.get(name) is None]
if missing:
    _fail(f"missing objects: {missing}")

attitude = scene.objects["Instrument_PFD_Attitude"]
if attitude.get("pfd_render_path") != "CIRCULAR_MASKED_GEOMETRY":
    _fail("masked-geometry PFD marker is absent")
if attitude.data is not None:
    _fail("PFD attitude transform must be an empty parent")

clip_mask = scene.objects["Instrument_PFD_ClipMask"]
if clip_mask.get("pfd_clip_path") != "OPAQUE_ANNULUS":
    _fail("physical PFD clip-mask marker is absent")
if len(clip_mask.data.vertices) != 128 or len(clip_mask.data.polygons) != 64:
    _fail("physical PFD clip mask is not the expected 64-segment annulus")
if not clip_mask.data.materials:
    _fail("physical PFD clip mask material is absent")

bezel = scene.objects["Instrument_PFD_Bezel"]
if abs(clip_mask.location.y - bezel.location.y) > 1.0e-6:
    _fail("PFD mask and bezel are not coplanar")

for name in ("Instrument_PFD_Sky", "Instrument_PFD_Ground"):
    surface = scene.objects[name]
    if surface.parent != attitude:
        _fail(f"{name} is not parented to the attitude transform")
    if len(surface.data.vertices) != 66 or len(surface.data.polygons) != 64:
        _fail(f"{name} is not the expected triangulated semicircle")

empty_game_strings = []
for obj in scene.objects:
    for prop in obj.game.properties:
        if prop.type == "STRING" and not prop.value:
            empty_game_strings.append(f"{obj.name}.{prop.name}")
if empty_game_strings:
    _fail(f"empty UPBGE string properties: {empty_game_strings}")

print(
    "ARRIETTY_BLEND_VALIDATION_OK",
    {
        "pfd_path": attitude.get("pfd_render_path"),
        "mask_vertices": len(clip_mask.data.vertices),
        "mask_faces": len(clip_mask.data.polygons),
        "empty_game_strings": 0,
    },
    flush=True,
)
