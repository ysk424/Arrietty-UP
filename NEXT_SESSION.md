# Next session handoff

Last updated: 2026-09-03 (Asia/Tokyo)

The panel, compiled C++ OpenXR bridge, PFD, human-powered flight controls, and
physical fan were accepted in live tests on 2026-09-03. The Arrietty-UP
simulator milestone is complete. Scenery work now moves to `../Secret-World`.
The copied `Tuval-1.blend` is the accepted initial screen: the rider starts at
Z=0 in the center of the Funafuti runway, facing along runway 03-21.

The agreed aircraft model is a human-powered glider with two ailerons, paired
elevator surfaces that move together, a rudder, and a pedal-driven pusher
propeller behind the pilot. Preserve that control and geometry model in future
work.

## Next repository

Continue world and scenery work from `C:\Users\azoo\git\Secret-World`.
The Arrietty-UP details below are retained as the accepted simulator reference.
Launch that reference from `C:\Users\azoo\git\Arrietty-UP` with `./start.ps1`.

The VR instrument panel is authored in the UPBGE scene and its placement was
accepted in OpenXR. The first live adjustment moved it
from 1.0 m to 1.3 m forward and increased its upward tilt from 26.565 to 46.565
degrees while retaining the 1.0 m center height. Its right-side debug block was
expanded to show steering, flight commands, tuning, voice, and fan status.

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

- Arrietty-UP version: `0.13.1-up.7`
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
no `P` press is required. `Esc` leaves the game. A darker rectangular game
border while running is expected.

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

The current build has 67 passing tests, including a source-boundary
test that rejects any `bpy` import under `arrietty_up`, panel formatting, PFD
attitude transforms, button chord handling, VIVE steering math, voice protocol,
HMD alignment math, pre-takeoff aileron feedback, and the connected flight
runtime. Fan protocol, slow-transition retry, diagnostics, safe shutdown, and
ground/flight airflow selection are also covered. Fan hardware acceptance is
complete. The production blend validator also checks the copied Tuvalu source
hash, Funafuti world, runway elevation/heading, active camera, and five ride
surfaces. Scenery and flight-ring work belong in `../Secret-World`.

Preserve unrelated user work in `../Arrietty` and `../Secret-World`.
