"""Render close-up masked-PFD checks without game or ride hardware."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


def _arguments():
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--pfd-output-dir", type=Path, required=True)
    parser.add_argument("--pfd-ortho-scale", type=float, default=0.31)
    return parser.parse_args(arguments)


def _set_attitude(attitude, pitch_degrees: float, bank_degrees: float):
    pitch = max(-12.0, min(12.0, pitch_degrees))
    rotation = math.radians(-bank_degrees)
    unbanked_z = -pitch * 0.004
    attitude.location = (
        math.sin(rotation) * unbanked_z,
        attitude.get("panel_base_y", 0.013),
        math.cos(rotation) * unbanked_z,
    )
    attitude.rotation_mode = "XYZ"
    attitude.rotation_euler = (0.0, rotation, 0.0)


def _camera_facing_disc(attitude, ortho_scale: float):
    center = attitude.matrix_world.translation
    axes = attitude.matrix_world.to_3x3()
    normal = (axes @ Vector((0.0, 1.0, 0.0))).normalized()
    up = (axes @ Vector((0.0, 0.0, 1.0))).normalized()
    up = (up - normal * up.dot(normal)).normalized()
    right = up.cross(normal).normalized()
    rotation = Matrix((right, up, normal)).transposed().to_quaternion()

    camera_data = bpy.data.cameras.new("ArriettyPFDCheckCameraData")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_scale
    camera = bpy.data.objects.new("ArriettyPFDCheckCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = center + normal * 0.5
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = rotation
    return camera


def main():
    options = _arguments()
    output_dir = options.pfd_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    attitude = scene.objects.get("Instrument_PFD_Attitude")
    if attitude is None:
        raise RuntimeError("ARRIETTY_PFD_RENDER_FAIL attitude group is absent")

    scene.camera = _camera_facing_disc(attitude, options.pfd_ortho_scale)
    # UPBGE keeps its Eevee engine identifier while upstream Blender calls the
    # equivalent engine BLENDER_EEVEE_NEXT.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.003, 0.003, 0.003)

    rendered = []
    for name, pitch, bank in (
        ("level", 0.0, 0.0),
        ("pitch_up_12", 12.0, 0.0),
        ("right_bank_25", 0.0, 25.0),
    ):
        _set_attitude(attitude, pitch, bank)
        bpy.context.view_layer.update()
        output = output_dir / f"pfd-{name}.png"
        scene.render.filepath = str(output)
        # Prime Eevee after moving the attitude group so the saved frame never
        # contains temporal data from the preceding check case.
        bpy.ops.render.render(write_still=False)
        bpy.ops.render.render(write_still=True)
        rendered.append(str(output))

    print("ARRIETTY_PFD_RENDER_OK", rendered, flush=True)


if __name__ == "__main__":
    main()
