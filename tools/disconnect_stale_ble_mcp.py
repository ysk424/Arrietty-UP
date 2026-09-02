"""Disconnect orphaned Arrietty BLE clients left by a closed event loop."""

import asyncio
import gc
import threading
import traceback


done = threading.Event()
outcome = {"disconnected": [], "errors": []}


targets = [
    client
    for client in gc.get_objects()
    if type(client).__module__ == "bleak"
    and type(client).__name__ == "BleakClient"
    and client.is_connected
    and getattr(client, "name", "") in {"T2 14000", "Forerunner"}
]


async def disconnect_targets():
    for client in targets:
        try:
            # The original callback belongs to an asyncio loop that has
            # already closed; invoking it would interrupt Bleak cleanup.
            client._backend._disconnected_callback = None
            await client.disconnect()
            outcome["disconnected"].append(
                {"name": client.name, "connected": client.is_connected}
            )
        except Exception:
            outcome["errors"].append(
                {"name": getattr(client, "name", "unknown"), "traceback": traceback.format_exc()}
            )


def worker():
    try:
        asyncio.run(disconnect_targets())
    finally:
        done.set()


threading.Thread(target=worker, name="ArriettyBLECleanup", daemon=True).start()


def check_is_finished():
    return outcome if done.is_set() else None
