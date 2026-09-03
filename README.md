# Arrietty-UP

The current session handoff and next starting point are recorded in
[`NEXT_SESSION.md`](NEXT_SESSION.md).

Arrietty-UP is the in-progress UPBGE port of `../Arrietty-UE`. Its target
surface is the bicycle, human-powered flight, OpenXR, CYCPLUS T2, VIVE
steering, wired ESP32 control panel, ESP32 fan, instrument, ride log, and
voice-PTT behavior. Cesium is not part of this repository; geographic world
streaming belongs to `../Secret-World`.

## Runtime boundary

- `bpy` is used only by authoring/build/startup tools, never by the game-frame
  package. A source-boundary test enforces this rule.
- Game-frame work uses UPBGE's `bge` API and the modules in `arrietty_up`.
- Ride transforms are copied from the UPBGE game object directly to persistent
  OpenXR navigation by compiled C++ `bge.logic` bridge functions. This avoids
  the previous per-frame `bpy.context`/RNA path.
- BLE and serial I/O run outside the render tick and publish immutable samples
  through queues.
- Core protocol, control, and flight calculations do not import Blender and
  are tested with the same values as `Arrietty-UE` v0.13.1.
- Standard Blender MCP remains on `127.0.0.1:9876`; UPBGE MCP uses
  `127.0.0.1:9877`.

## Current milestone

The locally built UPBGE 0.53/OpenXR path has been verified in an HMD. The
`tools/launch_openxr_game.py` startup helper starts persistent OpenXR before
entering the game once; returning with `Esc` works after restoring the View3D
context following XR notifier handling in the local UPBGE source tree. T2
speed-driven OpenXR navigation, Garmin heart rate, the wired controller, and
speed-driven fan levels have also passed a live run.

The game begins preparing and maintaining T2 as soon as its first UPBGE frame
runs; Button 1 aligns the HMD and centered VIVE handle, then arms movement.
Pedalling during preparation does not move the HMD or raise the fan level. The T2 worker uses the
installation's known address
`F8:10:89:93:10:C8`, with advertisement scanning as a fallback. It subscribes
to FTMS Indoor Bike Data before resistance control and optional CSC setup.
Garmin discovery begins in parallel as soon as T2 speed notifications are
active. Runtime properties expose `gatt_connected_after_seconds`,
`trainer_ready_after_seconds`, `first_ftms_after_seconds`, and
`control_ready_after_seconds` for one-run latency diagnosis. The separate
`first_motion_after_seconds` value measures Button 1 to actual motion.

## Port status

Live verified: persistent OpenXR game entry/exit, T2 FTMS ground movement,
Garmin heart rate, wired controls, forward-axis OpenXR navigation, HMD/VIVE
alignment, adjusted instrument-panel placement, and human-powered takeoff and
banked turning. The accepted afternoon 2026-09-03 run covered approximately
841.8 m, took off at 25.1 km/h, stepped the right-aileron bank command from
-1 through -10 degrees, turned as expected, and landed at 21.4 km/h.

The aircraft design target is a human-powered glider: two independently
commanded ailerons, left and right elevator surfaces moving together, a rudder,
and a pedal-driven pusher propeller behind the pilot. Flight-control behavior
and future visible aircraft geometry should preserve this arrangement.

OpenXR navigation now uses the compiled
`syncOpenXRNavigation`, `getOpenXRViewerRotation`,
`getOpenXRNavigationRotation`, and `resetOpenXRNavigation` APIs. The runtime
debug block must show `XR SYNCED`; `C++ BRIDGE MISSING` means the wrong UPBGE
binary was launched.

The next simulator task is the fan. World scenery, islands, flight rings, and
locations such as New York belong in `../Secret-World`, not this repository.

## Wired controls

Runtime operation intentionally has no numeric-keypad bindings. `P` starts the
game and `Esc` stops it safely; ride and flight operation use the wired panel:

- Button 1: align the current HMD view and centered VIVE handle, then start;
  press again for the approximately 2 m safety return.
- Button 2: switch between ground and human-powered flight; ground mode is
  blocked until the aircraft has landed.
- Button 3 / 4: left / right roll by 1 degree. Press both within 80 ms for
  pitch-up by 1 degree.
- Button 5: PTT down/up through the existing UDP voice bridge.
- Button 6: apply 3% T2 grade while held as the brake.
- Joystick 2: one center-to-edge gesture changes pitch or roll by 1 degree;
  its switch resets both commands.
- Joystick 1: its switch enters/advances/completes flight tuning; left/right
  gestures adjust the selected value one step.

## Instrument panel prototype

The three-section instrument panel is fixed to `ArriettyRuntime` (the bicycle
reference), centered 1.3 m forward at a height of 1.0 m and tilted upward
46.565 degrees. Its left section shows
heart rate and T2 power prominently, plus bicycle ground speed, applied T2
grade, and mode. The center is a PFD with vertical airspeed and altitude tapes;
its artificial horizon and pitch ladder move as ordinary UPBGE meshes behind a
fixed opaque circular annulus. The annulus and outer bezel are coplanar, so the
earth/sky presentation stays inside and centered in the aperture from an HMD
view. This physical mask replaced a GPU-node version that rendered correctly
on the desktop but appeared as a white circle in OpenXR. The right section
shows flight/physical values and runtime diagnostics. PFD pitch, bank, altitude,
centering, and banked flight were accepted in the 2026-09-03 HMD test.

Placement and viewing tilt are live custom-property controls on
`InstrumentPanelRoot`: `panel_forward_m`, `panel_center_height_m`, and
`panel_tilt_degrees`. Rebuild just the panel in an open or background UPBGE
scene with:

```powershell
& "C:\Users\azoo\git\build_upbge_windows_Release_x64_vc17_Release\bin\blender.exe" `
  --background "C:\Users\azoo\git\Arrietty-UP\Arrietty-UP.blend" `
  --python "C:\Users\azoo\git\Arrietty-UP\tools\build_instrument_panel.py"
```

Run Blender-independent tests with:

```bash
python3 -m unittest discover -s tests -v
```

For a live test, start SteamVR first and then run:

```powershell
& "C:\Users\azoo\git\Arrietty-UP\tools\launch_live_test.ps1"
```
