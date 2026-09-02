"""Non-blocking UDP controller for the ESP32 fan."""

from collections.abc import Callable
import math
import socket
import time

from . import constants as c


def level_for_speed(speed_kmh: float) -> int:
    if speed_kmh <= c.FAN_STOPPED_THRESHOLD_KMH:
        return 0
    fraction = max(0.0, min(1.0, speed_kmh / c.FAN_MAXIMUM_SPEED_KMH))
    return max(1, min(c.FAN_LEVEL_COUNT, math.ceil(fraction * c.FAN_LEVEL_COUNT)))


def parse_response_level(response: str) -> int | None:
    text = response.strip()
    upper = text.upper()
    prefix = "OK LEVEL " if upper.startswith("OK LEVEL ") else "OK SYNC " if upper.startswith("OK SYNC ") else None
    if prefix is None:
        return None
    first = text[len(prefix):].split(maxsplit=1)[0]
    if not first.isdecimal():
        return None
    level = int(first)
    return level if 0 <= level <= c.FAN_LEVEL_COUNT else None


class FanController:
    def __init__(
        self,
        socket_factory: Callable[..., socket.socket] = socket.socket,
        *,
        host: str = c.FAN_UDP_HOST,
        port: int = c.FAN_UDP_PORT,
    ) -> None:
        self._socket_factory = socket_factory
        self.destination = (host, port)
        self.socket: socket.socket | None = None
        self.last_requested_level: int | None = None
        self.requested_level = 0
        self.reported_level: int | None = None
        self.last_send_at: float | None = None
        self.last_response_at: float | None = None
        self.first_unanswered_send_at: float | None = None
        self.status = "NOT STARTED"

    @property
    def running(self) -> bool:
        return self.socket is not None

    def start(self) -> bool:
        self.stop()
        try:
            udp = self._socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
            udp.setblocking(False)
            udp.bind(("0.0.0.0", 0))
        except OSError as error:
            try:
                udp.close()
            except (OSError, UnboundLocalError):
                pass
            self.status = f"SOCKET ERROR: {error}"
            return False

        self.socket = udp
        self.last_requested_level = None
        self.requested_level = 0
        self.reported_level = None
        self.last_send_at = None
        self.last_response_at = None
        self.first_unanswered_send_at = None
        self.status = "WAITING FOR ESP32"
        return True

    def stop(self) -> None:
        udp = self.socket
        if udp is None:
            return
        self._send_command("LEVEL 0")
        udp.close()
        self.socket = None
        self.status = "STOPPED"

    def tick(self, speed_kmh: float, now: float | None = None) -> None:
        if self.socket is None:
            return
        now = time.monotonic() if now is None else now
        self._poll_responses(now)
        self.requested_level = level_for_speed(speed_kmh)
        resend_due = (
            self.last_send_at is None
            or now - self.last_send_at >= c.FAN_RESEND_SECONDS
        )
        if self.requested_level != self.last_requested_level or resend_due:
            if self._send_command(f"LEVEL {self.requested_level}"):
                self.last_requested_level = self.requested_level
                self.last_send_at = now
                if self.first_unanswered_send_at is None:
                    self.first_unanswered_send_at = now
                if self.last_response_at is None:
                    self.status = "WAITING FOR ESP32"
        self._poll_responses(now)

    def correct_reported_level(self, delta: int) -> None:
        base = self.requested_level if self.reported_level is None else self.reported_level
        corrected = max(0, min(c.FAN_LEVEL_COUNT, base + delta))
        self._send_command(f"SYNC {corrected}")
        self.requested_level = corrected
        self.reported_level = corrected
        self.last_requested_level = None
        self.status = "WAITING FOR SYNC ACK"

    def _send_command(self, command: str) -> bool:
        if self.socket is None:
            return False
        payload = command.encode("utf-8")
        try:
            return self.socket.sendto(payload, self.destination) == len(payload)
        except OSError as error:
            self.status = f"SEND ERROR: {error}"
            return False

    def _poll_responses(self, now: float) -> None:
        udp = self.socket
        if udp is None:
            return
        while True:
            try:
                payload, _sender = udp.recvfrom(1024)
            except BlockingIOError:
                break
            except OSError as error:
                self.status = f"RECEIVE ERROR: {error}"
                break
            level = parse_response_level(payload.decode("utf-8", errors="replace"))
            if level is None:
                continue
            self.reported_level = level
            self.last_response_at = now
            self.first_unanswered_send_at = None
            self.status = f"CONNECTED LEVEL {level}"

        if (
            self.first_unanswered_send_at is not None
            and now - self.first_unanswered_send_at >= 12.0
        ):
            self.status = "NO RESPONSE - CONNECT WI-FI Arrietty-Fan"
