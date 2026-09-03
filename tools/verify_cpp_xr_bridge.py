"""Smoke-test Arrietty's C++ OpenXR game API without starting hardware I/O.

Run this as a Blender ``--python`` startup script after loading the project.
It replaces the embedded bootstrap only in memory, enters the game for one
logic tick, exercises the compiled ``bge.logic`` functions, and exits without
saving the blend file.
"""

from __future__ import annotations

import bpy


_game_start_requested = False
_SMOKE_MODULE = "arrietty_cpp_xr_bridge_smoke"

_SMOKE_BOOTSTRAP = r'''
import bge

_done = False


def tick(controller):
    global _done
    if _done:
        return
    _done = True
    logic = bge.logic
    required = (
        "syncOpenXRNavigation",
        "getOpenXRViewerRotation",
        "getOpenXRNavigationRotation",
        "resetOpenXRNavigation",
    )
    missing = [name for name in required if not hasattr(logic, name)]
    if missing:
        print(f"ARRIETTY_CPP_XR_BRIDGE_FAIL missing={missing}", flush=True)
        logic.endGame()
        return

    try:
        synced = logic.syncOpenXRNavigation(controller.owner, 0.0)
        viewer = logic.getOpenXRViewerRotation()
        navigation = logic.getOpenXRNavigationRotation()
        reset = logic.resetOpenXRNavigation()
    except Exception as error:
        print(
            f"ARRIETTY_CPP_XR_BRIDGE_FAIL {type(error).__name__}: {error}",
            flush=True,
        )
    else:
        print(
            "ARRIETTY_CPP_XR_BRIDGE_OK "
            f"sync={synced} viewer={viewer} navigation={navigation} reset={reset}",
            flush=True,
        )
    logic.endGame()
'''


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


def _run_smoke_test():
    global _game_start_requested
    if _game_start_requested:
        return None

    context = _view3d_context()
    if context is None:
        return 0.25

    root = bpy.context.scene.objects.get("ArriettyRuntime")
    if root is None or not root.game.controllers:
        print("ARRIETTY_CPP_XR_BRIDGE_FAIL no runtime controller", flush=True)
        bpy.ops.wm.quit_blender()
        return None
    source = bpy.data.texts.get(f"{_SMOKE_MODULE}.py")
    if source is None:
        source = bpy.data.texts.new(f"{_SMOKE_MODULE}.py")
    source.clear()
    source.write(_SMOKE_BOOTSTRAP)
    root.game.controllers[0].mode = "MODULE"
    root.game.controllers[0].module = f"{_SMOKE_MODULE}.tick"

    _game_start_requested = True
    window, screen, area, region = context
    with bpy.context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
    ):
        result = bpy.ops.view3d.game_start()
    print(f"ARRIETTY_CPP_XR_BRIDGE_GAME_FINISHED {result}", flush=True)
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(_run_smoke_test, first_interval=0.5)
