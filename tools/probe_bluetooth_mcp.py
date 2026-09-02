"""Exercise the production T2/Garmin BLE worker, then disconnect cleanly."""

import sys
import time
from pathlib import Path


PROJECT = Path(r"C:\Users\azoo\git\Arrietty-UP")
DIGEST = (PROJECT / ".runtime" / "current.txt").read_text(encoding="ascii").strip()
DEPENDENCIES = PROJECT / ".runtime" / "site-packages" / DIGEST
for entry in (str(PROJECT), str(DEPENDENCIES)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from arrietty_up.bluetooth import BluetoothEventType, BluetoothManager


manager = BluetoothManager()
generation = manager.start(5, 0.0)
started = time.monotonic()
event_counts = {event_type.value: 0 for event_type in BluetoothEventType}
messages = []
first_event_seconds = {}
last_trainer = None
last_csc = None
last_heart_rate = None


def check_is_finished():
    global last_trainer, last_csc, last_heart_rate
    terminal_error = False
    for event in manager.drain_events():
        if event.generation != generation:
            continue
        event_counts[event.type.value] += 1
        first_event_seconds.setdefault(
            event.type.value,
            round(event.received_at - started, 3),
        )
        if event.message:
            messages.append(f"{event.type.value}: {event.message}")
        if event.type is BluetoothEventType.TRAINER_SAMPLE:
            sample = event.trainer_sample
            last_trainer = {
                "speed_kmh": sample.speed_kmh,
                "cadence_rpm": sample.cadence_rpm,
                "power_watts": sample.power_watts,
            }
        elif event.type is BluetoothEventType.CSC_SAMPLE:
            sample = event.csc_sample
            last_csc = {
                "wheel_revolutions": sample.wheel_revolutions,
                "wheel_event_time_ticks": sample.wheel_event_time_ticks,
                "crank_revolutions": sample.crank_revolutions,
                "crank_event_time_ticks": sample.crank_event_time_ticks,
            }
        elif event.type is BluetoothEventType.HEART_RATE_SAMPLE:
            last_heart_rate = event.heart_rate_bpm
        elif event.type is BluetoothEventType.ERROR:
            terminal_error = True

    complete = last_trainer is not None and last_heart_rate is not None
    elapsed = time.monotonic() - started
    if not complete and not terminal_error and elapsed < 30.0:
        return None

    stopped = manager.stop()
    for event in manager.drain_events():
        if event.generation == generation:
            event_counts[event.type.value] += 1
    return {
        "complete": complete,
        "stopped": stopped,
        "elapsed_seconds": round(elapsed, 3),
        "event_counts": event_counts,
        "first_event_seconds": first_event_seconds,
        "messages": messages[-12:],
        "trainer": last_trainer,
        "csc": last_csc,
        "heart_rate_bpm": last_heart_rate,
    }
