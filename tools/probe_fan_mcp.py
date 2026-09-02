"""Send a safe level-zero command to the live ESP32 fan through MCP."""

import sys
import time


PROJECT = r"C:\Users\azoo\git\Arrietty-UP"
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from arrietty_up.fan import FanController


fan = FanController()
started_ok = fan.start()
started = time.monotonic()


def check_is_finished():
    now = time.monotonic()
    fan.tick(0.0, now)
    if fan.reported_level is None and now - started < 5.0:
        return None
    outcome = {
        "started": started_ok,
        "status": fan.status,
        "requested_level": fan.requested_level,
        "reported_level": fan.reported_level,
        "elapsed_seconds": round(now - started, 3),
    }
    fan.stop()
    outcome["stopped"] = not fan.running
    return outcome
