"""Start persistent OpenXR first, then enter the UPBGE game.

Use as a Blender ``--python`` startup script after loading Arrietty-UP.blend.
The timer leaves Blender's initial file-load context before invoking either
operator and supplies an explicit View3D context for the game transition.
"""

from __future__ import annotations

import bpy


_attempt = 0
_xr_start_requested = False
_game_start_requested = False


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
    global _attempt, _xr_start_requested, _game_start_requested
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

    print("ARRIETTY_OPENXR_READY", flush=True)
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
