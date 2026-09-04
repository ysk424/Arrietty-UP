"""Align the editable Tuvalu test world with Arrietty-UP's runway-at-zero frame.

Run this with UPBGE after loading ``Tuval-1.blend``. The operation is
idempotent: it measures the current runway elevation and moves each top-level
object hierarchy only by the amount still needed to place the runway at Z=0.
"""

from __future__ import annotations

import json
import math

import bpy


WORLD_COLLECTION = "Secret World"
RUNWAY_OBJECT = "Funafuti Runway 03-21"
OCEAN_OBJECT = "Funafuti Deep Ocean"
EXPECTED_SOURCE_RUNWAY_Z_M = 1.46
TARGET_RUNWAY_Z_M = 0.0
TARGET_CONTENT_OFFSET_M = -EXPECTED_SOURCE_RUNWAY_Z_M


def _collection_tree(collection):
    yield collection
    for child in collection.children:
        yield from _collection_tree(child)


def _world_objects(collection) -> tuple:
    objects = []
    seen = set()
    for item in _collection_tree(collection):
        for obj in item.objects:
            if obj.name not in seen:
                seen.add(obj.name)
                objects.append(obj)
    return tuple(objects)


def _mesh_average_world_z(obj) -> float:
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not vertices:
        raise RuntimeError(f"Object has no vertices: {obj.name}")
    return sum(point.z for point in vertices) / len(vertices)


scene = bpy.context.scene
collection = bpy.data.collections.get(WORLD_COLLECTION)
runway = bpy.data.objects.get(RUNWAY_OBJECT)
ocean = bpy.data.objects.get(OCEAN_OBJECT)
if collection is None or runway is None or ocean is None:
    raise RuntimeError("Tuvalu test world, runway, or ocean is absent")

objects = _world_objects(collection)
object_set = set(objects)
runway_z_before = _mesh_average_world_z(runway)
delta_z = TARGET_RUNWAY_Z_M - runway_z_before
shift_needed = not math.isclose(delta_z, 0.0, abs_tol=1.0e-7)
changed = shift_needed
for obj in objects:
    if shift_needed and obj.parent not in object_set:
        obj.location.z += delta_z
    if not math.isclose(
        float(obj.get("secret_world_test_content_z_offset_m", math.inf)),
        TARGET_CONTENT_OFFSET_M,
        abs_tol=1.0e-7,
    ):
        obj["secret_world_test_content_z_offset_m"] = TARGET_CONTENT_OFFSET_M
        changed = True

bpy.context.view_layer.update()
runway_z_after = _mesh_average_world_z(runway)
ocean_z_after = _mesh_average_world_z(ocean)
if not math.isclose(runway_z_after, TARGET_RUNWAY_Z_M, abs_tol=1.0e-5):
    raise RuntimeError(f"Runway did not reach Z=0: {runway_z_after}")
if not math.isclose(ocean_z_after, TARGET_CONTENT_OFFSET_M, abs_tol=1.0e-5):
    raise RuntimeError(f"Ocean did not reach Z=-1.46: {ocean_z_after}")

for property_name in (
    "secret_world_test_content_z_offset_m",
    "secret_world_sea_level_z",
):
    if not math.isclose(
        float(scene.get(property_name, math.inf)),
        TARGET_CONTENT_OFFSET_M,
        abs_tol=1.0e-7,
    ):
        scene[property_name] = TARGET_CONTENT_OFFSET_M
        changed = True
if changed:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)
print(
    "ARRIETTY_TUVALU_TEST_WORLD_ALIGNED="
    + json.dumps(
        {
            "file": bpy.data.filepath,
            "objects": len(objects),
            "runway_z_before_m": runway_z_before,
            "applied_delta_z_m": delta_z,
            "runway_z_after_m": runway_z_after,
            "ocean_z_after_m": ocean_z_after,
            "saved": changed,
        },
        sort_keys=True,
    ),
    flush=True,
)
