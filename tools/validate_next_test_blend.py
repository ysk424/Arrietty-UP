"""Validate the authored blend before installing it for a live test."""

from __future__ import annotations

import bpy


def _fail(message: str) -> None:
    raise RuntimeError(f"ARRIETTY_BLEND_VALIDATION_FAIL {message}")


scene = bpy.context.scene
if scene.get("instrument_panel_version") != 2:
    _fail("instrument panel version is not 2")
required_objects = (
    "ArriettyRuntime",
    "InstrumentPanelRoot",
    "Instrument_PFD_Attitude",
    "Instrument_PFD_Bezel",
    "Instrument_PFDState",
    "Instrument_PhysicsText",
    "Instrument_DebugText",
)
missing = [name for name in required_objects if scene.objects.get(name) is None]
if missing:
    _fail(f"missing objects: {missing}")

obsolete = [
    name
    for name in (
        "Instrument_PFD_Horizon",
        "Instrument_PFD_Sky",
        "Instrument_PFD_Ground",
        "Instrument_PFD_Ladder",
    )
    if scene.objects.get(name) is not None
]
if obsolete:
    _fail(f"obsolete moving PFD objects remain: {obsolete}")

attitude = scene.objects["Instrument_PFD_Attitude"]
if attitude.get("pfd_render_path") != "FIXED_DISC_GPU_MATERIAL":
    _fail("fixed-disc PFD marker is absent")
if len(attitude.data.vertices) != 65 or len(attitude.data.polygons) != 64:
    _fail("fixed-disc PFD mesh is not the expected 64-segment triangle fan")
if not attitude.data.materials:
    _fail("fixed-disc PFD material is absent")
node_types = {
    node.bl_idname for node in attitude.data.materials[0].node_tree.nodes
}
for node_type in (
    "ShaderNodeTexCoord",
    "ShaderNodeObjectInfo",
    "ShaderNodeSeparateColor",
    "ShaderNodeBsdfPrincipled",
):
    if node_type not in node_types:
        _fail(f"PFD material node missing: {node_type}")

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
        "pfd_vertices": len(attitude.data.vertices),
        "pfd_triangles": len(attitude.data.polygons),
        "pfd_nodes": len(attitude.data.materials[0].node_tree.nodes),
        "empty_game_strings": 0,
    },
    flush=True,
)
