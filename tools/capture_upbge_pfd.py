"""Capture physically masked PFD states in UPBGE without ride hardware."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


_game_start_requested = False
_CAPTURE_MODULE = "arrietty_upbge_pfd_capture"


def _arguments():
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--pfd-output-dir", type=Path, required=True)
    parser.add_argument("--diagnostic-blend", type=Path)
    return parser.parse_args(arguments)


def _attitude_transform(pitch_degrees: float, bank_degrees: float):
    pitch = max(-12.0, min(12.0, pitch_degrees))
    rotation = math.radians(-bank_degrees)
    unbanked_z = -pitch * 0.004
    return (
        math.sin(rotation) * unbanked_z,
        math.cos(rotation) * unbanked_z,
        rotation,
    )


def _bootstrap(output_dir: Path) -> str:
    cases = (
        ("level", _attitude_transform(0.0, 0.0)),
        ("pitch_up_12", _attitude_transform(12.0, 0.0)),
        ("right_bank_25", _attitude_transform(0.0, 25.0)),
    )
    return f'''
import bge
from mathutils import Matrix, Vector

_frame = 0
_case_index = 0
_finish_frame = None
_advance_frame = None
_capture_frame = 15
_cases = {cases!r}
_output_dir = {str(output_dir)!r}


def set_attitude(attitude, transform):
    shift_x, shift_z, rotation = transform
    attitude.localPosition = (
        shift_x,
        attitude.get("panel_base_y", 0.013),
        shift_z,
    )
    attitude.localOrientation = Matrix.Rotation(rotation, 3, "Y")


def tick(controller):
    global _frame, _case_index, _finish_frame, _advance_frame, _capture_frame
    scene = bge.logic.getCurrentScene()
    try:
        attitude = scene.objects["Instrument_PFD_Attitude"]
    except (KeyError, SystemError):
        print("ARRIETTY_UPBGE_PFD_FAIL attitude group is absent", flush=True)
        bge.logic.endGame()
        return

    _frame += 1
    if _finish_frame is not None:
        if _frame >= _finish_frame:
            print("ARRIETTY_UPBGE_PFD_OK", flush=True)
            bge.logic.endGame()
        return
    if _advance_frame is not None and _frame >= _advance_frame:
        _case_index += 1
        set_attitude(attitude, _cases[_case_index][1])
        _capture_frame = _frame + 14
        _advance_frame = None
    if _frame == 1:
        camera = scene.active_camera
        axes = attitude.worldOrientation
        normal = (axes @ Vector((0.0, 1.0, 0.0))).normalized()
        up = (axes @ Vector((0.0, 0.0, 1.0))).normalized()
        up = (up - normal * up.dot(normal)).normalized()
        right = up.cross(normal).normalized()
        camera.worldPosition = attitude.worldPosition + normal * 0.5
        camera.worldOrientation = Matrix((right, up, normal)).transposed()
        camera.ortho_scale = 0.31
        print(
            "ARRIETTY_UPBGE_PFD_CAMERA "
            + str(tuple(round(v, 4) for v in camera.worldPosition)),
            flush=True,
        )
        set_attitude(attitude, _cases[_case_index][1])
    elif _frame == _capture_frame:
        name, transform = _cases[_case_index]
        path = _output_dir + "/upbge-pfd-" + name + ".png"
        bge.render.makeScreenshot(path)
        print(
            "ARRIETTY_UPBGE_PFD_CAPTURE "
            + name + " transform=" + str(tuple(round(v, 4) for v in transform)),
            flush=True,
        )
        _case_index += 1
        if _case_index >= len(_cases):
            # Standalone game-player screenshots are written after the frame.
            # Keep the engine alive briefly so the final capture is flushed.
            _finish_frame = _frame + 5
        else:
            # makeScreenshot captures the frame after this logic tick. Keep
            # the current uniform unchanged until that frame is complete.
            _case_index -= 1
            _advance_frame = _frame + 2
'''


def _install_capture_module(output_dir: Path) -> None:
    root = bpy.context.scene.objects.get("ArriettyRuntime")
    if root is None or not root.game.controllers:
        raise RuntimeError("ARRIETTY_UPBGE_PFD_FAIL no runtime controller")
    source = bpy.data.texts.get(f"{_CAPTURE_MODULE}.py")
    if source is None:
        source = bpy.data.texts.new(f"{_CAPTURE_MODULE}.py")
    source.clear()
    source.write(_bootstrap(output_dir))
    root.game.controllers[0].mode = "MODULE"
    root.game.controllers[0].module = f"{_CAPTURE_MODULE}.tick"


def _prepare_diagnostic_blend(options) -> None:
    options.pfd_output_dir.mkdir(parents=True, exist_ok=True)
    _install_capture_module(options.pfd_output_dir)
    attitude = bpy.context.scene.objects.get("Instrument_PFD_Attitude")
    camera = bpy.context.scene.camera
    if attitude is None or camera is None:
        raise RuntimeError("ARRIETTY_UPBGE_PFD_FAIL PFD or active camera is absent")
    bpy.context.view_layer.update()
    center = attitude.matrix_world.translation
    axes = attitude.matrix_world.to_3x3()
    normal = (axes @ Vector((0.0, 1.0, 0.0))).normalized()
    up = (axes @ Vector((0.0, 0.0, 1.0))).normalized()
    up = (up - normal * up.dot(normal)).normalized()
    right = up.cross(normal).normalized()
    camera.parent = None
    camera.matrix_parent_inverse.identity()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.31
    camera.location = center + normal * 0.5
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = Matrix((right, up, normal)).transposed().to_quaternion()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(options.diagnostic_blend),
        check_existing=False,
    )
    print(
        "ARRIETTY_UPBGE_PFD_DIAGNOSTIC_BLEND_OK",
        str(options.diagnostic_blend),
        flush=True,
    )


def _view3d_context():
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next(
                (candidate for candidate in area.regions if candidate.type == "WINDOW"),
                None,
            )
            if region is not None:
                return window, screen, area, region
    return None


def _run_capture():
    global _game_start_requested
    if _game_start_requested:
        return None
    context = _view3d_context()
    if context is None:
        return 0.25

    options = _arguments()
    options.pfd_output_dir.mkdir(parents=True, exist_ok=True)
    try:
        _install_capture_module(options.pfd_output_dir)
    except RuntimeError as error:
        print(str(error), flush=True)
        bpy.ops.wm.quit_blender()
        return None

    _game_start_requested = True
    window, screen, area, region = context
    with bpy.context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
    ):
        result = bpy.ops.view3d.game_start()
    print(f"ARRIETTY_UPBGE_PFD_GAME_FINISHED {result}", flush=True)
    bpy.ops.wm.quit_blender()
    return None


_options = _arguments()
if _options.diagnostic_blend is not None:
    _prepare_diagnostic_blend(_options)
else:
    bpy.app.timers.register(_run_capture, first_interval=0.5)
