"""Install the copied Tuvalu/Funafuti world into the UPBGE runtime scene.

This is an offline authoring tool. It uses :mod:`bpy` only while rebuilding
``Arrietty-UP.blend`` and does not become part of the game-frame package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SOURCE = PROJECT_ROOT / "arrietty_bootstrap.py"
DEFAULT_SOURCE = PROJECT_ROOT / "Tuval-1.blend"
DEFAULT_OUTPUT = PROJECT_ROOT / "Arrietty-UP.blend"
SOURCE_COLLECTION = "Secret World"
SOURCE_WORLD = "Secret World Funafuti Hero Sky"
INSTALLED_COLLECTION = "ArriettyTuvalWorld"
INSTALL_MARKER = "ArriettyTuvalInstall"
INSTALL_PROPERTY = "arrietty_tuval_installed"
VISUAL_ONLY_PROPERTY = "secret_world_visual_only"
RUNTIME_COLLISION_PROPERTY = "secret_world_runtime_collision"
RUNTIME_SHADOW_PROPERTY = "secret_world_runtime_cast_shadow"


def _arguments() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(arguments)


def _collection_tree(root) -> tuple:
    result = []
    pending = [root]
    while pending:
        collection = pending.pop()
        if collection in result:
            continue
        result.append(collection)
        pending.extend(collection.children)
    return tuple(result)


def _remove_previous_install(scene) -> None:
    for obj in tuple(bpy.data.objects):
        if obj.get(INSTALL_PROPERTY):
            bpy.data.objects.remove(obj, do_unlink=True)
    for collection in tuple(bpy.data.collections):
        if collection.get(INSTALL_PROPERTY):
            bpy.data.collections.remove(collection)
    if scene.world is not None and scene.world.get(INSTALL_PROPERTY):
        scene.world = None
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.lights,
        bpy.data.materials,
        bpy.data.node_groups,
        bpy.data.worlds,
    ):
        for datablock in tuple(datablocks):
            if datablock.get(INSTALL_PROPERTY) and datablock.users == 0:
                datablocks.remove(datablock)


def _remove_placeholder_world(scene) -> None:
    placeholder_names = {
        "SecretWorldRideSurface",
        "ArriettySun",
    }
    for obj in tuple(scene.objects):
        if (
            obj.name in placeholder_names
            or obj.name.startswith("CourseLine_")
            or obj.name.startswith("FlightMarker")
        ):
            bpy.data.objects.remove(obj, do_unlink=True)


def _world_objects(collection) -> tuple:
    objects = []
    seen = set()
    for item in _collection_tree(collection):
        for obj in item.objects:
            if obj.name not in seen:
                seen.add(obj.name)
                objects.append(obj)
    return tuple(objects)


def _runway_pose(runway) -> tuple[float, float]:
    vertices = [runway.matrix_world @ vertex.co for vertex in runway.data.vertices]
    if len(vertices) != 4:
        raise RuntimeError("Tuvalu runway is not the expected four-vertex surface")
    runway_elevation = sum(point.z for point in vertices) / len(vertices)
    forward_end = min(
        (
            (vertices[0] + vertices[1]) * 0.5,
            (vertices[2] + vertices[3]) * 0.5,
        ),
        key=lambda point: point.y,
    )
    initial_heading = math.degrees(math.atan2(forward_end.x, -forward_end.y))
    return runway_elevation, initial_heading


def _refresh_runtime_bootstrap() -> None:
    """Embed the current project-root-aware bootstrap in the prepared game."""
    if not BOOTSTRAP_SOURCE.is_file():
        raise RuntimeError(f"Arrietty bootstrap is absent: {BOOTSTRAP_SOURCE}")
    bootstrap = bpy.data.texts.get("arrietty_bootstrap.py")
    if bootstrap is None:
        bootstrap = bpy.data.texts.new("arrietty_bootstrap.py")
    bootstrap.clear()
    bootstrap.write(BOOTSTRAP_SOURCE.read_text(encoding="utf-8"))


def install(source: Path, output: Path) -> dict:
    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    scene = bpy.context.scene
    runtime = scene.objects.get("ArriettyRuntime")
    camera = scene.objects.get("ArriettyCamera")
    if runtime is None or camera is None:
        raise RuntimeError("Arrietty runtime/camera is absent from the target blend")

    _remove_previous_install(scene)
    _remove_placeholder_world(scene)

    with bpy.data.libraries.load(str(source), link=False) as (available, loaded):
        if SOURCE_COLLECTION not in available.collections:
            raise RuntimeError(f"source collection is absent: {SOURCE_COLLECTION}")
        if SOURCE_WORLD not in available.worlds:
            raise RuntimeError(f"source world is absent: {SOURCE_WORLD}")
        loaded.collections = [SOURCE_COLLECTION]
        loaded.worlds = [SOURCE_WORLD]

    world_collection = loaded.collections[0]
    tuval_world = loaded.worlds[0]
    if world_collection is None or tuval_world is None:
        raise RuntimeError("Tuvalu collection/world could not be appended")
    world_collection.name = INSTALLED_COLLECTION
    scene.collection.children.link(world_collection)
    # Appended objects can retain a stale identity matrix until the dependency
    # graph is evaluated. This matters when the editable test world already
    # carries the -1.46 m runway-at-zero offset in its object transforms.
    bpy.context.view_layer.update()

    imported_objects = _world_objects(world_collection)
    runway = next(
        (obj for obj in imported_objects if obj.name == "Funafuti Runway 03-21"),
        None,
    )
    if runway is None:
        raise RuntimeError("Funafuti runway is absent from the appended world")
    runway_elevation, initial_heading = _runway_pose(runway)
    source_content_z_offset = float(
        runway.get("secret_world_test_content_z_offset_m", -runway_elevation)
    )

    no_collision_meshes = 0
    static_ride_meshes = 0
    shadow_disabled_meshes = 0
    for collection in _collection_tree(world_collection):
        collection[INSTALL_PROPERTY] = True
    for obj in imported_objects:
        obj[INSTALL_PROPERTY] = True
        if obj.data is not None:
            obj.data[INSTALL_PROPERTY] = True
        for material_slot in obj.material_slots:
            if material_slot.material is not None:
                material_slot.material[INSTALL_PROPERTY] = True
        for modifier in obj.modifiers:
            if modifier.type == "NODES" and modifier.node_group is not None:
                modifier.node_group[INSTALL_PROPERTY] = True
        if obj.parent is None:
            obj.location.z -= runway_elevation
        if obj.get("secret_world_ride_surface"):
            obj["SecretWorldRideSurface"] = True
        if obj.type == "MESH":
            visual_only = bool(obj.get(VISUAL_ONLY_PROPERTY, False))
            collision_role = str(obj.get(RUNTIME_COLLISION_PROPERTY, ""))
            if visual_only or collision_role == "none":
                obj.game.physics_type = "NO_COLLISION"
                no_collision_meshes += 1
            elif obj.get("SecretWorldRideSurface"):
                obj.game.physics_type = "STATIC"
                static_ride_meshes += 1
            cast_shadow = bool(
                obj.get(RUNTIME_SHADOW_PROPERTY, not visual_only)
            )
            obj.visible_shadow = cast_shadow
            if not cast_shadow:
                shadow_disabled_meshes += 1

    marker = bpy.data.objects.new(INSTALL_MARKER, None)
    marker[INSTALL_PROPERTY] = True
    marker["source_blend"] = source.name
    marker["runway_elevation_offset_m"] = -runway_elevation
    marker["source_content_z_offset_m"] = source_content_z_offset
    marker["initial_heading_degrees"] = initial_heading
    marker["runtime_no_collision_meshes"] = no_collision_meshes
    marker["runtime_static_ride_meshes"] = static_ride_meshes
    marker["runtime_shadow_disabled_meshes"] = shadow_disabled_meshes
    scene.collection.objects.link(marker)

    tuval_world[INSTALL_PROPERTY] = True
    scene.world = tuval_world
    scene["arrietty_initial_world"] = "TUVALU_FUNAFUTI"
    scene["arrietty_world_source_blend"] = source.name
    scene["arrietty_world_source_sha256"] = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    scene["secret_world_origin_latitude_exact"] = -8.5239843
    scene["secret_world_origin_longitude_exact"] = 179.1967829
    scene["secret_world_origin_ellipsoid_height_exact_m"] = 34.8356
    scene["secret_world_test_content_z_offset_m"] = source_content_z_offset
    scene["secret_world_sea_level_z"] = source_content_z_offset

    runtime["initial_heading_degrees"] = initial_heading
    runtime.rotation_euler.z = math.radians(initial_heading)
    camera.data.clip_end = 250000.0
    scene.camera = camera
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            area.spaces.active.camera = camera
            area.spaces.active.region_3d.view_perspective = "CAMERA"

    _refresh_runtime_bootstrap()
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
    return {
        "saved": str(output),
        "source": str(source),
        "source_sha256": scene["arrietty_world_source_sha256"],
        "objects": len(imported_objects),
        "ride_surfaces": sum(
            bool(obj.get("SecretWorldRideSurface")) for obj in imported_objects
        ),
        "runway_elevation_offset_m": round(-runway_elevation, 6),
        "source_content_z_offset_m": round(source_content_z_offset, 6),
        "initial_heading_degrees": round(initial_heading, 6),
        "camera_clip_end_m": camera.data.clip_end,
        "no_collision_meshes": no_collision_meshes,
        "static_ride_meshes": static_ride_meshes,
        "shadow_disabled_meshes": shadow_disabled_meshes,
    }


if __name__ == "__main__":
    args = _arguments()
    result = install(args.source, args.output)
    print("ARRIETTY_TUVAL_INSTALL_OK " + json.dumps(result), flush=True)
