# Next session handoff

Last updated: 2026-09-03 (Asia/Tokyo)

The panel was implemented during the morning. A long live hardware/OpenXR test
window is expected after work this evening, as on 2026-09-02.

## Next live test

Work from `C:\Users\azoo\git\Arrietty-UP`.

The first VR instrument-panel prototype is now authored in the UPBGE scene.
Its Blender render and Blender-independent display tests pass, but it still
needs completion of its OpenXR/HMD fit test. The first live adjustment moved it
from 1.0 m to 1.3 m forward and increased its upward tilt from 26.565 to 46.565
degrees while retaining the 1.0 m center height. Confirm that the small
right-side debug text remains readable in both eyes and that dynamic values
update while T2, Garmin, and the fan are active.

Terrain may also be prepared as a visual reference, but its authoring source
should remain in Blender 5.2 LTS. Make a separate copy before opening or saving
it with the Blender 5.3 Alpha base used by UPBGE. Do not overwrite the 5.2
source with UPBGE 5.3.

Cesium/geographic world streaming belongs to `../Secret-World`; do not port it
into this repository. Everything else needed by the Arrietty experience is in
scope here.

## Working baseline

- Arrietty-UP version: `0.13.1-up.2`
- Public repository: https://github.com/ysk424/Arrietty-UP
- Accepted baseline commit before this handoff: `6bb494009434a6f95bd74ee51d569f1b8a2a5304`
- Standard Blender: locally built Blender 5.2.0 LTS
- UPBGE build base: Blender 5.3.0 Alpha / UPBGE 0.53
- Standard Blender MCP: `127.0.0.1:9876`
- UPBGE MCP: `127.0.0.1:9877`

Launch the UPBGE project from PowerShell with:

```powershell
& "C:\Users\azoo\git\build_upbge_windows_Release_x64_vc17_Release\bin\blender.exe" --online-mode "C:\Users\azoo\git\Arrietty-UP\Arrietty-UP.blend"
```

`P` starts the UPBGE game. `Esc` leaves the game. A darker rectangular game
border while running is expected. The OpenXR image should remain present in
the HMD across both operations.

## Live hardware result

The final integrated hardware run on 2026-09-02 was accepted as **PASS**.

- OpenXR remained displayed while entering and leaving the UPBGE game.
- CYCPLUS T2 speed data produced ground movement in the HMD.
- The wired controller's Button 1 armed movement; Numpad 0 is the keyboard
  equivalent.
- The speed-driven ESP32 fan reacted to detected speed.
- Garmin heart-rate reception and both ESP32 devices were operational.
- Last observed wired controller connection: `COM7`, 115200 bps.
- HMD forward travel for this scene is world `Y-`.

The game starts and maintains the T2 connection from its first frame. Button 1
or Numpad 0 only arms movement, so a long BLE setup must not block the user's
start action. T2 FTMS speed notification is the critical path. Garmin scanning,
resistance control, and optional CSC initialization happen later or in
parallel; it is acceptable for Garmin and the fan to become ready after motion
starts. Garmin broadcasting can stop when it is not actively communicated
with, so keep the runtime connection active during a test.

Connection phase timings are exposed through runtime properties, including
`gatt_connected_after_seconds`, `trainer_ready_after_seconds`,
`first_ftms_after_seconds`, `control_ready_after_seconds`, and
`first_motion_after_seconds`. Use these instead of estimating a delay by eye.

The second Button 1/Numpad 0 safety-return behavior is implemented and unit
tested. Give it a dedicated measured live check before relying on it as a
finished feature.

## Important local fixes and backups

The local UPBGE OpenXR fix restores the View3D context after XR notifier
handling in `source/gameengine/Ketsji/KX_Scene.cpp`.

- Local UPBGE fix commit: `6f0e68ccbb60e3b666025c75a49b7b0b769f7ed2`
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

The current baseline has 43 passing tests, including panel formatting and PFD
attitude-transform tests. Flight physics and digital/tuning controls are unit
tested but are not yet connected to the UPBGE game loop. Remaining integrations
include VIVE steering, flight runtime, ride CSV, voice PTT, course-surface
collision, presets, and VR alerts.

Preserve unrelated user work in `../Arrietty` and `../Secret-World`.
