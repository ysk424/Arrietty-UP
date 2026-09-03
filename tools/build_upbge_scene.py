"""Author the initial Arrietty-UP scene inside interactive UPBGE.

Run through ``tools/mcp_client.py --file``. This is authoring code, so using
``bpy`` here does not put it in the game-frame path.
"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


OUTPUT = Path(r"C:\Users\azoo\git\Arrietty-UP\Arrietty-UP.blend")
BOOTSTRAP = Path(r"C:\Users\azoo\git\Arrietty-UP\arrietty_bootstrap.py")


def material(name, color, emission=0.0):
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    principled = value.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.65
        principled.inputs["Emission Color"].default_value = color
        principled.inputs["Emission Strength"].default_value = emission
    return value


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    for datablock in tuple(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)

scene = bpy.context.scene
scene.name = "ArriettyUP"
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.game_settings.use_viewport_render = True
scene.game_settings.exit_key = "ESC"
scene.world.color = (0.015, 0.02, 0.035)
scene["arrietty_source"] = "Arrietty-UE 0.13.1"
scene["arrietty_cesium"] = False

ground_material = material("RideSurfaceMaterial", (0.035, 0.04, 0.045, 1.0))
line_material = material("CourseLineMaterial", (0.04, 0.9, 0.3, 1.0), 0.4)
marker_material = material("MarkerMaterial", (1.0, 0.16, 0.03, 1.0), 0.6)

bpy.ops.mesh.primitive_plane_add(size=80.0, location=(0.0, 0.0, 0.0))
ground = bpy.context.object
ground.name = "SecretWorldRideSurface"
ground["SecretWorldRideSurface"] = True
ground.data.materials.append(ground_material)

for y in range(-30, 31, 3):
    bpy.ops.mesh.primitive_cube_add(location=(0.0, float(y), 0.015), scale=(0.035, 0.9, 0.015))
    dash = bpy.context.object
    dash.name = f"CourseLine_{y:+03d}"
    dash.data.materials.append(line_material)

for position in ((-3.0, -8.0, 1.0), (3.0, -8.0, 1.0), (-4.5, -16.0, 1.5), (4.5, -16.0, 1.5)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=position)
    marker = bpy.context.object
    marker.name = "FlightMarker"
    marker.data.materials.append(marker_material)

bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 0.0))
root = bpy.context.object
root.name = "ArriettyRuntime"
root["arrietty_status"] = "AUTHORING"

bpy.context.view_layer.objects.active = root
root.select_set(True)
bpy.ops.logic.sensor_add(type="ALWAYS", name="ArriettyTick", object=root.name)
sensor = root.game.sensors[-1]
sensor.use_pulse_true_level = True
bpy.ops.logic.sensor_add(type="KEYBOARD", name="ArriettySafeExit", object=root.name)
exit_sensor = root.game.sensors[-1]
exit_sensor.key = "ESC"
bpy.ops.logic.controller_add(type="PYTHON", name="ArriettyRuntime", object=root.name)
controller = root.game.controllers[-1]
controller.mode = "MODULE"
bootstrap = bpy.data.texts.get("arrietty_bootstrap.py")
if bootstrap is None:
    bootstrap = bpy.data.texts.new("arrietty_bootstrap.py")
bootstrap.clear()
bootstrap.write(BOOTSTRAP.read_text(encoding="utf-8"))
controller.module = "arrietty_bootstrap.tick"
sensor.link(controller)
exit_sensor.link(controller)

bpy.ops.object.camera_add(location=(0.0, 0.0, 1.5))
camera = bpy.context.object
camera.name = "ArriettyCamera"
camera.data.clip_start = 0.05
camera.data.clip_end = 5000.0
look_at(camera, (0.0, -8.0, 1.5))
camera.parent = root
scene.camera = camera

# Keep a full scene rebuild and the incremental panel builder in sync.
if str(OUTPUT.parent) not in sys.path:
    sys.path.insert(0, str(OUTPUT.parent))
from tools.build_instrument_panel import build_panel

build_panel(scene)

bpy.ops.object.light_add(type="SUN", location=(0.0, 0.0, 20.0))
sun = bpy.context.object
sun.name = "ArriettySun"
sun.rotation_euler = (math.radians(28.0), math.radians(-22.0), math.radians(35.0))
sun.data.energy = 2.2

bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), check_existing=False)
from tools.install_tuval_world import install as install_tuval_world

tuval_result = install_tuval_world(OUTPUT.parent / "Tuval-1.blend", OUTPUT)
result = {
    "saved": str(OUTPUT),
    "objects": len(scene.objects),
    "controller": controller.module,
    "viewport_render": scene.game_settings.use_viewport_render,
    "initial_world": tuval_result["source"],
}
