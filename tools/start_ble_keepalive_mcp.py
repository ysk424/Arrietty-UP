"""Keep the production BLE worker alive in Blender between MCP calls."""

import sys
from pathlib import Path

import bpy


PROJECT = Path(r"C:\Users\azoo\git\Arrietty-UP")
DIGEST = (PROJECT / ".runtime" / "current.txt").read_text(encoding="ascii").strip()
DEPENDENCIES = PROJECT / ".runtime" / "site-packages" / DIGEST
for entry in (str(PROJECT), str(DEPENDENCIES)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from arrietty_up.bluetooth import BluetoothManager


namespace = bpy.app.driver_namespace
previous = namespace.get("arrietty_ble_keepalive")
if previous is not None:
    previous.stop()

manager = BluetoothManager()
generation = manager.start(5, 0.0)
namespace["arrietty_ble_keepalive"] = manager

result = {"started": manager.running, "generation": generation}
