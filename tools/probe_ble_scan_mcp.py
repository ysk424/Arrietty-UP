"""Scan for T2 and BLE Heart Rate advertisements without connecting."""

import asyncio
import sys
import threading
import traceback
from pathlib import Path


PROJECT = Path(r"C:\Users\azoo\git\Arrietty-UP")
DIGEST = (PROJECT / ".runtime" / "current.txt").read_text(encoding="ascii").strip()
DEPENDENCIES = PROJECT / ".runtime" / "site-packages" / DIGEST
for entry in (str(PROJECT), str(DEPENDENCIES)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


done = threading.Event()
outcome = {"seen_count": 0, "seen_names": [], "t2": [], "ftms": [], "heart_rate": [], "error": None}
heart_rate_uuid = "0000180d-0000-1000-8000-00805f9b34fb"
ftms_uuid = "00001826-0000-1000-8000-00805f9b34fb"


async def scan():
    from bleak import BleakScanner

    devices = await BleakScanner.discover(timeout=8.0, return_adv=True)
    outcome["seen_count"] = len(devices)
    for device, advertisement in devices.values():
        name = device.name or advertisement.local_name or ""
        if name:
            outcome["seen_names"].append(name)
        service_uuids = [uuid.lower() for uuid in advertisement.service_uuids]
        if "t2" in name.lower():
            outcome["t2"].append({"name": name, "services": service_uuids})
        if ftms_uuid in service_uuids:
            outcome["ftms"].append({"name": name, "services": service_uuids})
        if heart_rate_uuid in service_uuids:
            outcome["heart_rate"].append({"name": name, "services": service_uuids})
    outcome["seen_names"] = sorted(set(outcome["seen_names"]))


def worker():
    try:
        asyncio.run(scan())
    except Exception:
        outcome["error"] = traceback.format_exc()
    finally:
        done.set()


threading.Thread(target=worker, name="ArriettyBLEScanProbe", daemon=True).start()


def check_is_finished():
    return outcome if done.is_set() else None
