# Next session handoff

Last updated: 2026-09-03 (Asia/Tokyo)

The panel placement and human-powered flight controls were accepted in live
OpenXR tests. The morning 2026-09-03 run achieved takeoff and controlled turns.
The next-test build replaces per-frame `bpy` OpenXR access with a compiled C++
bridge and replaces the moving PFD geometry with one fixed circular GPU disc.

## Next live test

Work from `C:\Users\azoo\git\Arrietty-UP`.

The first VR instrument-panel prototype is now authored in the UPBGE scene and
its placement was accepted in OpenXR. The first live adjustment moved it
from 1.0 m to 1.3 m forward and increased its upward tilt from 26.565 to 46.565
degrees while retaining the 1.0 m center height. Its right-side debug block was
expanded to show steering, flight commands, tuning, and voice status. Confirm
that those small dynamic values remain readable in both eyes.

There are no numeric-keypad runtime controls. Start with
`tools/launch_live_test.ps1` as shown below. With the HMD facing the physical
bicycle direction and the handle centered, use Button 1 to align/start.

For the next live test, first confirm the right-side debug block says
`XR SYNCED`. Compare the PFD directly with the numeric PITCH/BANK/ALT values:
pitch-up must move the horizon downward, bank must rotate the horizon opposite
the aircraft bank, and no sky/earth or pitch mark may leave the circular disc.
Also confirm that HMD translation/rotation remains smooth while pedalling and
turning. The older geometry escaped the circular bezel; the fixed GPU disc is
intended to eliminate that failure and now needs HMD verification.

Terrain may also be prepared as a visual reference, but its authoring source
should remain in Blender 5.2 LTS. Make a separate copy before opening or saving
it with the Blender 5.3 Alpha base used by UPBGE. Do not overwrite the 5.2
source with UPBGE 5.3.

Cesium/geographic world streaming belongs to `../Secret-World`; do not port it
into this repository. Everything else needed by the Arrietty experience is in
scope here.

## Working baseline

- Arrietty-UP version: `0.13.1-up.4`
- Public repository: https://github.com/ysk424/Arrietty-UP
- Accepted and pushed working baseline: `58c0031`
- Standard Blender: locally built Blender 5.2.0 LTS
- UPBGE build base: Blender 5.3.0 Alpha / UPBGE 0.53
- Standard Blender MCP: `127.0.0.1:9876`
- UPBGE MCP: `127.0.0.1:9877`

After starting SteamVR, launch OpenXR and enter the game once with:

```powershell
& "C:\Users\azoo\git\Arrietty-UP\tools\launch_live_test.ps1"
```

The launcher starts the persistent OpenXR session before entering the game, so
no `P` press is required. `Esc` leaves the game. A darker rectangular game
border while running is expected.

## Live hardware result

The morning flight run on 2026-09-03 was accepted as a **working baseline with
the previous moving-geometry PFD issue**. The next-test build addresses it but
has not yet been accepted in the HMD.

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

The current next-test build has 60 passing tests, including a source-boundary
test that rejects any `bpy` import under `arrietty_up`, panel formatting, PFD
attitude transforms, button chord handling, VIVE steering math, voice protocol,
HMD alignment math, and the connected flight runtime. Remaining integrations
include live verification of the C++ OpenXR bridge and fixed-disc PFD, ride CSV,
course-surface collision, resistance-preset selection, and VR alerts.

Preserve unrelated user work in `../Arrietty` and `../Secret-World`.
