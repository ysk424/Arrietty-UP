"""Validate the authored blend before installing it for a live test."""

from __future__ import annotations

import hashlib
from pathlib import Path

import bpy


def _fail(message: str) -> None:
    raise RuntimeError(f"ARRIETTY_BLEND_VALIDATION_FAIL {message}")


scene = bpy.context.scene
if scene.get("instrument_panel_version") != 4:
    _fail("instrument panel version is not 4")
required_objects = (
    "ArriettyRuntime",
    "ArriettyCamera",
    "ArriettyTuvalInstall",
    "Funafuti Runway 03-21",
    "InstrumentPanelRoot",
    "Instrument_ElapsedValue",
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

if scene.get("arrietty_initial_world") != "TUVALU_FUNAFUTI":
    _fail("Tuvalu/Funafuti is not the initial world")
source_blend = Path(bpy.data.filepath).parent / "Tuval-1.blend"
if not source_blend.is_file():
    _fail("copied Tuval-1.blend is absent")
source_hash = hashlib.sha256(source_blend.read_bytes()).hexdigest()
if source_hash != scene.get("arrietty_world_source_sha256"):
    _fail("Tuval-1.blend does not match the installed world source")
if scene.world is None or not scene.world.get("arrietty_tuval_installed"):
    _fail("Tuvalu sky world is not active")

runtime = scene.objects["ArriettyRuntime"]
camera = scene.objects["ArriettyCamera"]
if abs(float(runtime.get("initial_heading_degrees", 0.0)) + 43.075085) > 1.0e-4:
    _fail("initial heading is not aligned with the Funafuti runway")
if scene.camera != camera or camera.data.clip_end < 200000.0:
    _fail("initial camera is not configured for the Tuvalu world")
runway = scene.objects["Funafuti Runway 03-21"]
runway_z = sum((runway.matrix_world @ vertex.co).z for vertex in runway.data.vertices)
runway_z /= len(runway.data.vertices)
if abs(runway_z) > 1.0e-4:
    _fail("Funafuti runway surface is not aligned to Z=0")
ocean = scene.objects.get("Funafuti Deep Ocean")
if ocean is None:
    _fail("Funafuti deep ocean is absent")
ocean_z = sum((ocean.matrix_world @ vertex.co).z for vertex in ocean.data.vertices)
ocean_z /= len(ocean.data.vertices)
if abs(ocean_z + 1.46) > 1.0e-4:
    _fail("Funafuti sea level is not aligned to Z=-1.46")
if abs(float(scene.get("secret_world_test_content_z_offset_m", 0.0)) + 1.46) > 1.0e-4:
    _fail("Tuvalu test-world content offset is not -1.46 m")
ride_surfaces = [
    obj for obj in scene.objects if obj.get("SecretWorldRideSurface")
]
if len(ride_surfaces) != 5:
    _fail(f"expected 5 Tuvalu ride surfaces, found {len(ride_surfaces)}")
if scene.objects.get("SecretWorldRideSurface") is not None:
    _fail("placeholder ride plane was not removed")

elapsed = scene.objects["Instrument_ElapsedValue"]
elapsed_property = next(
    (prop for prop in elapsed.game.properties if prop.name == "Text"), None
)
if elapsed_property is None or elapsed_property.value != "0:00:00":
    _fail("elapsed display does not begin at 0:00:00")

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
        "initial_world": scene.get("arrietty_initial_world"),
        "ride_surfaces": len(ride_surfaces),
        "runway_z": round(runway_z, 6),
        "ocean_z": round(ocean_z, 6),
    },
    flush=True,
)
