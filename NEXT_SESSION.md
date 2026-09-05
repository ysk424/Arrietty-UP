# Next session handoff

Last updated: 2026-09-05 (Asia/Tokyo)

## Latest-session route log (2026-09-05)

The user accepted the solar/preflight workflow as **PASS**, then requested a
flight route log that overwrites previous runs. Implemented
`arrietty_up/flight_log.py`: `logs/latest-flight.csv`, one sample per second
plus the final position, replaced on the first frame of each P game session.
Button 1 does not truncate it. CSV contains ENU position, simulator altitude,
bearing/speed/state, actual UTC and editor-exported world/local-time/origin
metadata. A bounded background queue keeps disk writes off the game thread.
Esc and editor game_post close the writer. No bpy imports were added to runtime.
See `docs/FLIGHT_LOG.md` for exact columns, retention and failure behavior.

Previously there were diagnostics and an in-memory recovery trail, but no
persistent route, so the accepted flight has no recoverable route CSV.
Launcher diagnostics now use fixed `logs/latest-console.out.log` and
`logs/latest-console.err.log`; older timestamped TEMP logs were not deleted.
These changes take effect on the next normal UPBGE launch; the currently
accepted session was not restarted. Tests: 78 unittest cases pass;
Secret World's `tests/upbge_world_setup.py` passes including metadata export.
Hardware flight-log acceptance is pending the next actual flight.

The user requested documentation and PUSH before starting a separate route
project. Suggested repository name: `Arrietty-trajectory`, preferred over
`Arrietty-path` for actual time/altitude-bearing flight history. Naming remains
unconfirmed; no new repository was created here. The CSV above is the input
contract available for that future project; visualization scope is not yet set.

Update after the user's next flight: the separate repository is now
`https://github.com/ysk424/Arrietty-trajectory` (private), authorized by the user.
Its first scope is standard-Blender replay with a thin plate and chase camera.
The actual latest CSV was read and copied to that project's ignored
`build/accepted-flight.csv`; SHA-256
`aa308362845d2a6292669a7f0b119bd60ed3b195572cfdf88e5509d60170438d`.
163 post-start samples span 163.677 seconds, reach 32.717 m altitude and end
at logged distance 1042.478 m. The final forced point and clean runtime exit
are present, so first-flight CSV persistence is now verified. Arrietty-UP
source/log were not modified by the replay project. Continue animation work
in `../Arrietty-trajectory/docs/PROJECT_STATE.md`; this repository retains
ownership of live flight telemetry and equipment.

End of 2026-09-05: the user marked the standard-Blender replay **合格** and
will return the following morning. Arrietty-trajectory saved the accepted
editor state in `work/Accepted-Replay-20260905.blend`, verified read-back, and
closed Blender. Continue from its `docs/PROJECT_STATE.md` and open that saved
work file. No new live flight or UPBGE startup is needed to replay it. Logging
and device ownership remain here; model/camera animation belongs there.

## New preflight local-time workflow (2026-09-05)

The user approved replacing automatic game start with editor waiting:
OpenXR starts, `N > Arrietty` opens, local date/time is applied, then P starts
play and Esc returns to setup. `tools/world_setup_ui.py` owns only editor UI
and lifecycle; `../Secret-World/solar.py` owns astronomy/sky/Sun/disc. The
Secret World launcher passes `SECRET_WORLD_SOLAR_MODULE`. World time remains
fixed in play; no `bpy` or time-of-day work was added to `arrietty_up`.

The default prepared solar scene uses 2026-09-05 17:45 Tuvalu time (UTC+12).
Inputs are date YYYY-MM-DD and time HH:MM. Press **日時を適用** before P;
unapplied edits block the custom start operator. **ゲーム開始（P）** is also
available. Esc keeps OpenXR running and restores the applied sky for editing.
Standalone `start.ps1` also waits for P, but the solar adapter requires the
integrated Secret World launcher. The startup timer ends before manual play,
so it no longer spans the nested game loop.

Validation: `python -m unittest discover -s tests` passed 75 tests, including
the new no-autostart assertion and unchanged no-bpy runtime boundary.
`../Secret-World/tests/upbge_world_setup.py` passed in headless UPBGE.
A live OpenXR lifecycle probe entered the game, inspected the Sun on a game
frame, ended after 90 frames, and returned to usable setup with OpenXR still
running. The probe temporarily replaced the game tick, so this was not a
hardware flight test. Original `arrietty_bootstrap.tick` was restored and the
probe text removed. The user subsequently reported **PASS** on 2026-09-05;
the fixed-time sun and preflight workflow are accepted. No numeric FPS result
was supplied. The accepted Secret World Runtime is `20260905102318005`.

The historical automatic-start descriptions below refer to the earlier
accepted baseline; use the workflow above for current builds.

The panel, compiled C++ OpenXR bridge, PFD, human-powered flight controls, and
physical fan were accepted in live tests on 2026-09-03. The Arrietty-UP
simulator milestone is complete. Scenery work now moves to `../Secret-World`.
The copied `Tuval-1.blend` is the accepted initial screen: the rider starts at
Z=0 in the center of the Funafuti runway, facing along runway 03-21.
The final completion run launched from `start.ps1`, took off, landed, and
confirmed that the Button 1 elapsed clock starts at `0:00:00`; the user marked
the completed simulator **PASS**.

On 2026-09-05 the PFD gained a horizontal geographic heading tape, a magenta
home marker pointing back to the current game session's start position, and a
red `STALL 18` km/h display. The compass converts the internal Y-minus vehicle
heading to Secret World's East-North-Up geographic bearing. Dynamic updates use
the existing UPBGE `bge` runtime path; there is no game-frame `bpy` import and
no UPBGE rebuild is required. The expanded panel passed unit, source-boundary,
blend-structure, and offline render checks. Secret World's Runtime build
`20260904095413055` was prepared successfully with Arrietty source hash prefix
`24218aedf38a`. The 2026-09-05 OpenXR/HMD flight launched through
`../Secret-World/start_arrietty_up.ps1`; the user confirmed that the heading was
readable in flight and accepted the result as **PASS**. The runtime then stopped
cleanly.

The agreed aircraft model is a human-powered glider with two ailerons, paired
elevator surfaces that move together, a rudder, and a pedal-driven pusher
propeller behind the pilot. Preserve that control and geometry model in future
work.

## Next repository

Continue world and scenery work from `C:\Users\azoo\git\Secret-World`.
The Arrietty-UP details below are retained as the accepted simulator reference.
Launch that reference from `C:\Users\azoo\git\Arrietty-UP` with `./start.ps1`.
For the current integrated HMD test, use
`C:\Users\azoo\git\Secret-World\start_arrietty_up.ps1` instead.

The VR instrument panel is authored in the UPBGE scene and its placement was
accepted in OpenXR. The first live adjustment moved it
from 1.0 m to 1.3 m forward and increased its upward tilt from 26.565 to 46.565
degrees while retaining the 1.0 m center height. Its right-side debug block was
expanded to show steering, flight commands, tuning, voice, and fan status.
The left section includes an `ELAPSED H:MM:SS` clock that resets to zero on the
first Button 1 start and continues through ground and flight modes.

There are no numeric-keypad runtime controls. Start with
`tools/launch_live_test.ps1` as shown below. With the HMD facing the physical
bicycle direction and the handle centered, use Button 1 to align/start.

The completed fan behavior passed hardware acceptance. The current runtime
uses ground speed while riding and simulated airspeed while flying, waits for
slow IR transitions without UDP flooding, exposes command/response diagnostics,
and sends a three-packet level 0 safety stop. `bpy` remains forbidden from the
game-frame path.

Terrain may also be prepared as a visual reference, but its authoring source
should remain in Blender 5.2 LTS. Make a separate copy before opening or saving
it with the Blender 5.3 Alpha base used by UPBGE. Do not overwrite the 5.2
source with UPBGE 5.3.

Cesium/geographic world streaming belongs to `../Secret-World`; do not port it
into this repository. Everything else needed by the Arrietty experience is in
scope here.

## Working baseline

- Arrietty-UP version: `0.13.1-up.10`
- Public repository: https://github.com/ysk424/Arrietty-UP
- Accepted working baseline: current `main` HEAD
- Standard Blender: locally built Blender 5.2.0 LTS
- UPBGE build base: Blender 5.3.0 Alpha / UPBGE 0.53
- Standard Blender MCP: `127.0.0.1:9876`
- UPBGE MCP: `127.0.0.1:9877`

After starting SteamVR, launch OpenXR and enter the game once with:

```powershell
& "C:\Users\azoo\git\Arrietty-UP\start.ps1"
```

The launcher starts the persistent OpenXR session before entering the game, so
no `P` press is required. `Esc` leaves the game. The startup timer deliberately
remains registered during the nested game loop, preventing the prior
`BLI_timer_execute` access violation after returning to Blender. A darker
rectangular game border while running is expected.
The launcher now forces the required UPBGE Viewport Render path and selects
Rendered shading before starting OpenXR; `-Shading Solid` is the low-load
fallback. Button 1 keeps retrying HMD alignment until a valid rendered pose is
available, and the panel shows `HMD WAIT` or `HMD OK` beside XR status.

Generated Secret World integration blends may live outside this repository.
`tools/launch_live_test.ps1` now passes `ARRIETTY_PROJECT_ROOT` only to the
launched process, and the embedded bootstrap prefers that explicit root when
loading `arrietty_up` and `.runtime` dependencies. The Tuvalu installer refreshes
the embedded bootstrap whenever it prepares a game blend. This prevents an
external blend directory from being mistaken for the Arrietty-UP project root.

Secret World Runtime Converter v0.2.0 adds the `flight_v1` optimization
contract. The installer maps visual-only world meshes to `NO_COLLISION`, keeps
only the five ride surfaces as `STATIC`, and applies the converter's shadow
roles. The accepted source remains untouched; generated integration blends are
validated outside this repository. Build `20260904095413055` produced 59
one-kilometre scenery chunks, 61 no-collision/no-shadow visual meshes, and six
lightweight runtime materials. The Secret World converter now applies the
island `SOLIDIFY` and rejects every remaining world modifier. The 2026-09-05
live HMD flight accepted the integrated heading display in this prepared world.

## Live hardware result

The focused fan run on 2026-09-03 was accepted as **PASS**.

- Windows connected to `Arrietty-Fan` as `192.168.4.2`.
- A safe level-0 probe received `CONNECTED LEVEL 0` before moving the fan.
- The commanded and observed physical sequence was `0→1→2→3→4→5→6→0`.
- Every ESP32 acknowledgement was received; each one-level IR transition took
  approximately 1.69 seconds.
- The final level-0 acknowledgement was followed by three additional level-0
  safety datagrams.

The afternoon flight run on 2026-09-03 was accepted as **PASS**.

- OpenXR and the native C++ bridge reported `READY` / `XR SYNCED`.
- CYCPLUS T2, Garmin heart rate, and the wired controller on `COM7` connected.
- The run covered approximately 841.8 m, took off at 25.1 km/h, and landed at
  21.4 km/h.
- Button 4 stepped the right-aileron command from -1 through -10 degrees;
  aircraft bank, PFD horizon, and the resulting turn matched the rider's intent.
- The PFD physical aperture mask kept sky, earth, and pitch marks inside the
  circle, and placing the mask and bezel on one depth plane corrected the HMD
  center offset.
- A final `start.ps1` run took off and landed in the Funafuti world, and the
  added elapsed clock was accepted as **PASS**.
- A GPU-node PFD attempted earlier in the same test rendered as a white circle
  in OpenXR and is intentionally not the accepted implementation.

The morning flight run on 2026-09-03 remains the earlier working baseline.

- OpenXR appeared in the HMD and the game entered exactly once.
- CYCPLUS T2 and the wired controller connected; the last controller port was
  `COM7` at 115200 bps.
- Human-powered takeoff and controlled turns were achieved.
- Right-side physics/debug values reflected the flight well enough to operate.

The integrated hardware run on 2026-09-02 was also accepted as **PASS**.

- OpenXR remained displayed while entering and leaving the UPBGE game.
- CYCPLUS T2 speed data produced ground movement in the HMD.
- The wired controller's Button 1 armed movement.
- The speed-driven ESP32 fan reacted to detected speed.
- Garmin heart-rate reception and both ESP32 devices were operational.
- Last observed wired controller connection: `COM7`, 115200 bps.
- HMD forward travel for this scene is world `Y-`.

The game starts and maintains the T2 connection from its first frame. Button 1
aligns/arms movement, so a long BLE setup must not block the user's start
action. T2 FTMS speed notification is the critical path. Garmin scanning,
resistance control, and optional CSC initialization happen later or in
parallel; it is acceptable for Garmin and the fan to become ready after motion
starts. Garmin broadcasting can stop when it is not actively communicated
with, so keep the runtime connection active during a test.

Connection phase timings are exposed through runtime properties, including
`gatt_connected_after_seconds`, `trainer_ready_after_seconds`,
`first_ftms_after_seconds`, `control_ready_after_seconds`, and
`first_motion_after_seconds`. Use these instead of estimating a delay by eye.

The second Button 1 safety-return behavior is implemented and unit tested. Give
it a dedicated measured live check before relying on it as a finished feature.

## Important local fixes and backups

The local UPBGE OpenXR fix restores the View3D context after XR notifier
handling in `source/gameengine/Ketsji/KX_Scene.cpp`.

- Local UPBGE fix commit: `6f0e68ccbb60e3b666025c75a49b7b0b769f7ed2`
- Native game-side OpenXR bridge commit: `7b63ea539c`
- Private compact recovery snapshot: https://github.com/ysk424/upbge
- Public upstream report: https://github.com/UPBGE/upbge/issues/2044
- Upstream fix: `2d1b28a92646a6bd1eab38e331285690526b1797`; issue closed as
  completed on 2026-09-04. No further action is planned.

The full upstream history was intentionally not copied to the private
repository. The private snapshot contains the complete modified source file,
the exact patch, upstream base commit, license, and restoration instructions.

The MCP polling fix prevents the UPBGE game transition from repeatedly raising
`ModuleNotFoundError: No module named 'bl_ext'`.

- MCP fix commit: `f610a0950958306dda88ce1c2702be8ccf8109f0`
- Private backup: https://github.com/ysk424/blender-mcp-port-switch

The `bge_netlogic` and `bge_bricknodes` add-on warnings seen at startup were
non-fatal during the accepted run.

## Verification and remaining work

Run Blender-independent tests with:

```bash
python3 -m unittest discover -s tests -v
```

The current build has 78 passing tests, including a source-boundary
test that rejects any `bpy` import under `arrietty_up`, panel formatting, PFD
attitude transforms, button chord handling, VIVE steering math, voice protocol,
HMD alignment math, pre-takeoff aileron feedback, and the connected flight
runtime. Elapsed-time reset/formatting and re-entrant launcher-timer safety are
also covered. Fan protocol, slow-transition retry, diagnostics, safe shutdown,
and ground/flight airflow selection are also covered. Fan hardware acceptance
is complete. The production blend validator also checks the copied Tuvalu
source hash, Funafuti world, runway elevation/heading, active camera, and five
ride surfaces. Scenery and flight-ring work belong in `../Secret-World`.

Preserve unrelated user work in `../Arrietty` and `../Secret-World`.
