# Arrietty-UP

Arrietty-UP is the in-progress UPBGE port of `../Arrietty-UE`. Its target
surface is the bicycle, human-powered flight, OpenXR, CYCPLUS T2, VIVE
steering, wired ESP32 control panel, ESP32 fan, instrument, ride log, and
voice-PTT behavior. Cesium is not part of this repository; geographic world
streaming belongs to `../Secret-World`.

## Runtime boundary

- `bpy` is used only by authoring/build tools that create or update `.blend`
  data.
- Game-frame work uses UPBGE's `bge` API and the modules in `arrietty_up`.
- Ride transforms are mirrored to Blender's OpenXR navigation pose because the
  persistent XR session does not follow a moved UPBGE camera automatically.
- BLE and serial I/O run outside the render tick and publish immutable samples
  through queues.
- Core protocol, control, and flight calculations do not import Blender and
  are tested with the same values as `Arrietty-UE` v0.13.1.
- Standard Blender MCP remains on `127.0.0.1:9876`; UPBGE MCP uses
  `127.0.0.1:9877`.

## Current milestone

The locally built UPBGE 0.53/OpenXR path has been verified in an HMD. Starting
the game with `P`, keeping the XR image alive, and returning with `Esc` works
after restoring the View3D context following XR notifier handling in the local
UPBGE source tree. T2 speed-driven OpenXR navigation, Garmin heart rate, the
wired controller, and speed-driven fan levels have also passed a live run.

The game begins preparing and maintaining T2 as soon as its first UPBGE frame
runs; Button 1 or Numpad 0 only arms movement. Pedalling during preparation
does not move the HMD or raise the fan level. The T2 worker uses the
installation's known address
`F8:10:89:93:10:C8`, with advertisement scanning as a fallback. It subscribes
to FTMS Indoor Bike Data before resistance control and optional CSC setup.
Garmin discovery begins in parallel as soon as T2 speed notifications are
active. Runtime properties expose `gatt_connected_after_seconds`,
`trainer_ready_after_seconds`, `first_ftms_after_seconds`, and
`control_ready_after_seconds` for one-run latency diagnosis. The separate
`first_motion_after_seconds` value measures Button 1/Numpad 0 to actual motion.

## Port status

Live verified: persistent OpenXR game entry/exit, T2 FTMS ground movement,
Garmin heart rate, wired Button 1, speed-driven fan output, and forward-axis
OpenXR navigation. Implemented and unit tested but awaiting the next live run:
early T2/Garmin preparation, direct-address T2 connection, speed-first GATT
setup, connection phase timings, and the two-meter safety return.

The flight physics and digital/tuning control calculations are unit tested but
not yet connected to the UPBGE game loop. VIVE steering, the VR instrument,
ride CSV, voice PTT, course-surface collision, presets, and VR alerts remain to
be integrated. This list describes the implementation state; the target
feature list above is not a claim that those items are already complete.

Run Blender-independent tests with:

```bash
python3 -m unittest discover -s tests -v
```
