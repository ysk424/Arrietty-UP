"""Run the production serial worker briefly through Blender MCP."""

import sys
import time


PROJECT = r"C:\Users\azoo\git\Arrietty-UP"
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from arrietty_up.serial_controller import ControllerEventType, SerialController


controller = SerialController()
collected = []
started = time.monotonic()
controller.start()


def check_is_finished():
    collected.extend(controller.drain_events())
    have_sample = any(event.type is ControllerEventType.SAMPLE for event in collected)
    if not have_sample and time.monotonic() - started < 6.0:
        return None

    stopped = controller.stop()
    collected.extend(controller.drain_events())
    return {
        "have_sample": have_sample,
        "stopped": stopped,
        "events": [
            {
                "type": event.type.value,
                "message": event.message,
                "port": event.port,
                "sequence": event.sample.sequence if event.sample else None,
                "buttons": event.sample.button_mask if event.sample else None,
            }
            for event in collected
        ],
    }
