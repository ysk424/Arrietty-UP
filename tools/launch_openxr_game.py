"""Start persistent OpenXR first, then enter the UPBGE game.

Use as a Blender ``--python`` startup script after loading Arrietty-UP.blend.
The timer leaves Blender's initial file-load context before invoking either
operator and supplies an explicit View3D context for the game transition.
"""

from __future__ import annotations

import os

import bpy


_attempt = 0
_xr_start_requested = False
_xr_ready_announced = False
_game_start_requested = False
_wait_for_google_tiles = os.environ.get(
    "ARRIETTY_WAIT_FOR_GOOGLE_TILES", "0"
).strip() == "1"
_google_wait_announced = False


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


def _start_openxr_then_game():
    global _attempt, _xr_start_requested, _xr_ready_announced
    global _game_start_requested, _google_wait_announced
    # Entering the game engine pumps Blender events, so this timer can be
    # invoked again before game_start() returns. Mark the transition first.
    # A re-entrant call must keep the timer alive: unregistering it there frees
    # the outer callback's storage and crashes in BLI_timer_execute when the
    # game later returns. The outer call unregisters normally after game exit.
    if _game_start_requested:
        return 3600.0

    _attempt += 1
    context = _view3d_context()
    if context is None:
        if _attempt >= 40:
            print("ARRIETTY_LAUNCH_ERROR no View3D context", flush=True)
            return None
        return 0.5

    window, screen, area, region = context
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
    _game_start_requested = True
    with bpy.context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
    ):
        result = bpy.ops.view3d.game_start()
    print(f"ARRIETTY_GAME_FINISHED {result}", flush=True)
    return None


bpy.app.timers.register(_start_openxr_then_game, first_interval=0.5)
