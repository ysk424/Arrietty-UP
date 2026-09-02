"""Trace each Win32 serial handshake stage through Blender MCP."""

import sys
import threading
import time
import traceback


PROJECT = r"C:\Users\azoo\git\Arrietty-UP"
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from arrietty_up.serial_controller import Win32SerialPort


done = threading.Event()
stop = threading.Event()
trace = {"phases": [], "lines": [], "error": None}


def worker():
    port = None
    try:
        trace["phases"].append("opening")
        port = Win32SerialPort("COM7")
        trace["phases"].append("opened")
        port.purge(transmit=True)
        trace["phases"].append("purged_all")
        stop.wait(1.2)
        port.purge(transmit=False)
        trace["phases"].append("purged_rx")
        port.send_line("PING\n")
        trace["phases"].append("ping_sent")
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and len(trace["lines"]) < 16:
            line = port.read_line(0.25, stop)
            if line is not None:
                trace["lines"].append(line)
                if line == "PONG ARRIETTY-CONTROLLER/1":
                    trace["phases"].append("identified")
                    break
    except Exception:
        trace["error"] = traceback.format_exc()
    finally:
        if port is not None:
            port.close()
            trace["phases"].append("closed")
        done.set()


threading.Thread(target=worker, name="ArriettySerialTrace", daemon=True).start()


def check_is_finished():
    if not done.is_set():
        return None
    return trace
