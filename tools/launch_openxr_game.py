"""Start persistent OpenXR and wait for preflight setup and P.

Use as a Blender ``--python`` startup script after loading Arrietty-UP.blend.
The timer leaves Blender's initial file-load context before invoking either
operator and supplies an explicit View3D context for the game transition.
"""

from __future__ import annotations

import os
from pathlib import Path
import runpy

import bpy


_attempt = 0
_xr_start_requested = False
_xr_ready_announced = False
_wait_for_google_tiles = os.environ.get(
    "ARRIETTY_WAIT_FOR_GOOGLE_TILES", "0"
).strip() == "1"
_requested_shading = os.environ.get(
    "ARRIETTY_XR_SHADING", "RENDERED"
).strip().upper()
if _requested_shading not in {"SOLID", "RENDERED"}:
    raise RuntimeError(
        "ARRIETTY_XR_SHADING must be RENDERED or SOLID, "
        f"not {_requested_shading!r}"
    )
_google_wait_announced = False
_render_mode_announced = False
_setup_ready = False


def _google_tiles_ready():
    return any(
        bool(obj.get("secret_world_google_live", False))
        for obj in bpy.data.objects
    )


def _view3d_context():
    window_manager = bpy.context.window_manager
    for window in window_manager.windows:
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


def _configure_render_mode(area):
    """Select the OpenXR-capable UPBGE path before either session starts."""
    global _render_mode_announced

    scene = bpy.context.scene
    scene.game_settings.use_viewport_render = True
    area.spaces.active.shading.type = _requested_shading
    xr_shading = bpy.context.window_manager.xr_session_settings.shading
    xr_shading.type = _requested_shading
    if _requested_shading == "RENDERED":
        xr_shading.use_scene_lights_render = True
        xr_shading.use_scene_world_render = True
    if not _render_mode_announced:
        print(
            "ARRIETTY_RENDER_MODE "
            f"game=VIEWPORT shading={_requested_shading}",
            flush=True,
        )
        _render_mode_announced = True


def _start_openxr_then_game():
    global _attempt, _xr_start_requested, _xr_ready_announced
    global _google_wait_announced
    global _setup_ready
    _attempt += 1
    context = _view3d_context()
    if context is None:
        if _attempt >= 40:
            print("ARRIETTY_LAUNCH_ERROR no View3D context", flush=True)
            return None
        return 0.5

    window, screen, area, region = context
    _configure_render_mode(area)
    if not _setup_ready:
        runpy.run_path(str(Path(__file__).with_name('world_setup_ui.py')))['register']()
        _setup_ready = True
    xr_state = bpy.context.window_manager.xr_session_state
    xr_running = xr_state is not None and xr_state.is_running(bpy.context)
    if not xr_running:
        if not _xr_start_requested:
            with bpy.context.temp_override(
                window=window,
                screen=screen,
                area=area,
                region=region,
            ):
                result = bpy.ops.wm.xr_session_toggle()
            _xr_start_requested = True
            print(f"ARRIETTY_OPENXR_START {result}", flush=True)
        if _attempt >= 40:
            print("ARRIETTY_LAUNCH_ERROR OpenXR did not start", flush=True)
            return None
        return 0.5

    if not _xr_ready_announced:
        print("ARRIETTY_OPENXR_READY", flush=True)
        _xr_ready_announced = True
    if _wait_for_google_tiles and not _google_tiles_ready():
        if not _google_wait_announced:
            print(
                "ARRIETTY_WAITING_FOR_GOOGLE_TILES "
                "Use N > Secret World > Paste Google Tiles",
                flush=True,
            )
            _google_wait_announced = True
        return 0.5
    if _wait_for_google_tiles:
        print("ARRIETTY_GOOGLE_TILES_READY", flush=True)
    print('ARRIETTY_WAITING_FOR_PLAY Apply local date/time, then press P',flush=True)
    return None


bpy.app.timers.register(_start_openxr_then_game, first_interval=0.5)
