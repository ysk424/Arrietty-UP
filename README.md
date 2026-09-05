# Arrietty-UP

The current session handoff and next starting point are recorded in
[`NEXT_SESSION.md`](NEXT_SESSION.md).

Arrietty-UP is the in-progress UPBGE port of `../Arrietty-UE`. Its target
surface is the bicycle, human-powered flight, OpenXR, CYCPLUS T2, VIVE
steering, wired ESP32 control panel, ESP32 fan, instrument, ride log, and
voice-PTT behavior. Cesium is not part of this repository; geographic world
streaming belongs to `../Secret-World`.

Flight routes are saved once per second to `logs/latest-flight.csv`. Each new
P game session replaces the previous route; Esc saves the final position.
See [flight-log details](docs/FLIGHT_LOG.md). Launcher console logs also use
fixed names in `logs/` and are replaced on each UPBGE process launch.

## Start

Start SteamVR, power the bicycle equipment, and run this from PowerShell:

```powershell
.\start.ps1
```

The root launcher checks SteamVR and residual Blender processes, opens the
accepted `Arrietty-UP.blend` with the locally built UPBGE, starts persistent
OpenXR, and waits in the editor. Press `P` over the 3D View to enter the game;
`Esc` returns to setup. It always uses
UPBGE's OpenXR-capable Viewport Render path and selects Rendered shading before
the XR session starts. For a lower-load diagnostic run, use
`.\start.ps1 -Shading Solid`.

To paste RAM-only Google tiles before the game starts, use the same PowerShell
session in which `SECRET_WORLD_GOOGLE_MAPS_API_KEY` was set:

```powershell
.\start.ps1 -WaitForGoogleTiles
```

The launcher starts OpenXR and remains in the UPBGE editor. Use
`N > Secret World > Paste Google Tiles`; after the paste completes, the
press `P` to enter the game.

For the current island and local-time controls, launch
`../Secret-World/start_arrietty_up.ps1`. The `N > Arrietty` panel opens
automatically. Enter a date (`YYYY-MM-DD`) and Tuvalu local time (`HH:MM`,
UTC+12), click **日時を適用**, then press **P** or **ゲーム開始（P）**.
Changing input without applying it prevents accidental start with the old time.
The selected world time stays fixed during play. After **Esc**, the same
settings can be edited and applied again. The normal Button 1 flight alignment
and arming sequence still applies after entering the game.

The editor-only adapter is `tools/world_setup_ui.py`. It loads the world-owned
solar module from `SECRET_WORLD_SOLAR_MODULE`, supplied by the Secret World
launcher. No solar or `bpy` work was added to the per-frame game package.

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
`tools/launch_openxr_game.py` startup helper starts persistent OpenXR and waits
for `P`; returning with `Esc` works after restoring the View3D
context following XR notifier handling in the local UPBGE source tree. T2
speed-driven OpenXR navigation, Garmin heart rate, the wired controller, and
speed-driven fan levels have also passed a live run.

The game begins preparing and maintaining T2 as soon as its first UPBGE frame
runs; Button 1 aligns the HMD and centered VIVE handle, then arms movement.
If a Rendered scene takes time to publish its first valid HMD pose, alignment
keeps waiting instead of expiring after one second. The debug panel reports
`HMD WAIT` until alignment succeeds and `HMD OK` afterwards.
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
alignment, adjusted instrument-panel placement, the Button 1 elapsed clock,
and human-powered takeoff and banked turning. The final completion run launched
through `start.ps1`, took off, landed, and confirmed the elapsed clock begins at
`0:00:00`; it was accepted as PASS on 2026-09-03. The accepted afternoon run
covered approximately 841.8 m, took off at 25.1 km/h, stepped the right-aileron
bank command from -1 through -10 degrees, turned as expected, and landed at
21.4 km/h.

The aircraft design target is a human-powered glider: two independently
commanded ailerons, left and right elevator surfaces moving together, a rudder,
and a pedal-driven pusher propeller behind the pilot. Flight-control behavior
and future visible aircraft geometry should preserve this arrangement.

OpenXR navigation now uses the compiled
`syncOpenXRNavigation`, `getOpenXRViewerRotation`,
`getOpenXRNavigationRotation`, and `resetOpenXRNavigation` APIs. The runtime
debug block must show `XR SYNCED`; `C++ BRIDGE MISSING` means the wrong UPBGE
binary was launched.

The physical fan, the final simulator integration, passed its focused hardware
acceptance on 2026-09-03. The Arrietty-UP simulator milestone is complete.
The copied `Tuval-1.blend` is installed as the initial Funafuti runway world.
Further scenery authoring, flight rings, and locations such as New York belong
in `../Secret-World`; Arrietty-UP keeps only the accepted runtime snapshot.

## Initial Tuvalu world

`Tuval-1.blend` is the UPBGE test-world copy derived from
`../Arrietty/test_data/Tuval-1.blend`. The reproducible
`tools/lower_tuvalu_test_world.py` conversion places its runway at `Z=0` and
sea level at `Z=-1.46 m`, matching Secret World's default Google tile offset.
Its `Secret World` collection and Funafuti sky are appended without another
vertical shift, start at the runway center facing along 03-21, extend the
camera range to 250 km, and tag five imported ground objects as ride surfaces.
The original Blender 5.2 LTS source under `../Arrietty/test_data` remains
unchanged.

Reinstall the copied world after a full scene rebuild with:

```powershell
& "C:\Users\azoo\git\build_upbge_windows_Release_x64_vc17_Release\bin\blender.exe" `
  --background ".\Arrietty-UP.blend" `
  --python ".\tools\install_tuval_world.py"
```

## Physical fan

The ESP32-IR controller is reached over UDP at `192.168.4.1:4210` while the PC
is connected to the `Arrietty-Fan` Wi-Fi network. Airflow maps 0–30 km/h to
levels 0–6. Ground mode follows bicycle ground speed; flight mode follows
simulated glider airspeed, including unpowered gliding.

Fan I/O is nonblocking and does not use `bpy`. The runtime waits for the
ESP32's `OK LEVEL` acknowledgement without flooding commands during its slow
IR level transition, reports requested/actual levels on the panel, retries a
missing response, and sends `LEVEL 0` three times during shutdown.

With the bicycle/game stopped, test the physical controller from Windows:

```powershell
py -3 .\tools\test_fan_hardware.py --levels 0 1 2 3 4 5 6 0
```

The test requires an acknowledgement for every level and always requests
level 0 in its cleanup path. Running it without `--levels` performs only the
safe level-0 connection check.

The accepted hardware run commanded `0→1→2→3→4→5→6→0`. The ESP32 acknowledged
every level, each IR step completed in approximately 1.69 seconds, the rider
observed the same physical sequence, and the fan stopped at level 0.

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
grade, mode, and elapsed time from Button 1 start. The elapsed clock begins at
`0:00:00` and continues through ground and flight modes. The center is a PFD
with vertical airspeed and altitude tapes and a horizontal geographic heading
tape. The compass uses Secret World's East-North-Up axes, so its cardinal
values are true local bearings (`N=000`, `E=090`, `S=180`, `W=270`). A magenta
`H` marker moves toward the bearing back to the position where the game session
began; when that bearing is outside the visible tape it remains at the
applicable edge as `<H` or `H>`. The airspeed tape also displays the modeled
`STALL 18` km/h speed in red. These live values use the existing UPBGE `bge`
game API and never import `bpy` during a game frame; `bpy` is used only by the
offline panel-building tool.

The PFD's artificial horizon and pitch ladder move as ordinary UPBGE meshes
behind a fixed opaque circular annulus. The annulus and outer bezel are coplanar, so the
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
& ..\Secret-World\start_arrietty_up.ps1
```
