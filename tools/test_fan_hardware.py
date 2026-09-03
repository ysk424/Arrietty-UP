"""Exercise the ESP32 fan with acknowledged, safely stopped level commands.

Run this from Windows while connected to the ``Arrietty-Fan`` Wi-Fi network.
The default command only verifies level zero. Pass an explicit level sequence
to perform a moving test.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arrietty_up import constants as c
from arrietty_up.fan import FanController


def _fan_level(value: str) -> int:
    level = int(value)
    if not 0 <= level <= c.FAN_LEVEL_COUNT:
        raise argparse.ArgumentTypeError(
            f"level must be between 0 and {c.FAN_LEVEL_COUNT}"
        )
    return level


def _wait_for_level(
    fan: FanController,
    level: int,
    timeout_seconds: float,
) -> float:
    started = time.monotonic()
    deadline = started + timeout_seconds
    previous_status = ""
    while True:
        now = time.monotonic()
        fan.set_level(level, now)
        if fan.status != previous_status:
            print(
                "ARRIETTY_FAN_TEST_STATUS "
                f"requested={level} reported={fan.reported_level} "
                f"status={fan.status}",
                flush=True,
            )
            previous_status = fan.status
        if fan.reported_level == level and fan.connected:
            return now - started
        if now >= deadline:
            raise TimeoutError(
                f"fan did not acknowledge level {level}: {fan.status}"
            )
        time.sleep(0.02)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test the Arrietty ESP32 fan over non-blocking UDP.",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        type=_fan_level,
        default=[0],
        help="acknowledged level sequence (default: safe level 0 only)",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=0.5,
        help="time to hold each acknowledged level",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=c.FAN_RESPONSE_TIMEOUT_SECONDS + 3.0,
        help="maximum acknowledgement time per level",
    )
    parser.add_argument(
        "--host",
        default=c.FAN_UDP_HOST,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=c.FAN_UDP_PORT,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    if args.hold_seconds < 0.0 or args.timeout_seconds <= 0.0:
        parser.error("hold time must be nonnegative and timeout must be positive")

    fan = FanController(host=args.host, port=args.port)
    if not fan.start():
        print(f"ARRIETTY_FAN_TEST_FAIL {fan.status}", flush=True)
        return 1

    try:
        for level in args.levels:
            elapsed = _wait_for_level(fan, level, args.timeout_seconds)
            print(
                "ARRIETTY_FAN_TEST_ACK "
                f"level={level} elapsed={elapsed:.3f}s "
                f"sent={fan.packets_sent} received={fan.packets_received}",
                flush=True,
            )
            if args.hold_seconds:
                time.sleep(args.hold_seconds)
    except (OSError, TimeoutError) as error:
        print(f"ARRIETTY_FAN_TEST_FAIL {error}", flush=True)
        return 1
    finally:
        sent_before_stop = fan.packets_sent
        fan.stop()
        print(
            "ARRIETTY_FAN_TEST_STOP "
            f"level=0 packets={fan.packets_sent - sent_before_stop}",
            flush=True,
        )

    print("ARRIETTY_FAN_TEST_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
