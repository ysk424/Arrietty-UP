"""UPBGE game-loop entry point.

This module deliberately imports :mod:`bge` only inside the controller entry
point so the rest of the package remains testable in normal Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import time

from . import constants as c
from .bluetooth import BluetoothEvent, BluetoothEventType, BluetoothManager
from .controls import DigitalFlightControls, FlightTuningControls
from .controller_protocol import ButtonEdgeLatch
from .flight import initialize_human_powered_flight
from .fan import FanController
from .instruments import update_upbge_panel
from .models import CscSample, FlightState
from .serial_controller import ControllerEventType, SerialController
from .trainer_protocol import effective_speed_kmh


@dataclass(slots=True)
class RuntimeState:
    started_at: float = field(default_factory=time.monotonic)
    previous_tick_at: float = field(default_factory=time.monotonic)
    frame_count: int = 0
    flight_enabled: bool = False
    flight: FlightState = field(default_factory=initialize_human_powered_flight)
    digital_controls: DigitalFlightControls = field(default_factory=DigitalFlightControls)
    tuning_controls: FlightTuningControls = field(default_factory=FlightTuningControls)
    serial: SerialController = field(default_factory=SerialController)
    bluetooth: BluetoothManager = field(default_factory=BluetoothManager)
    fan: FanController = field(default_factory=FanController)
    button_edges: ButtonEdgeLatch = field(default_factory=ButtonEdgeLatch)
    button_history: list[str] = field(default_factory=list)
    controller_sample_count: int = 0
    controller_nonzero_samples: int = 0
    controller_button_mask: int = 0
    ride_active: bool = False
    connection_started_at_seconds: float = 0.0
    ride_started_at_seconds: float = 0.0
    first_motion_after_seconds: float = 0.0
    trainer_found_after_seconds: float = 0.0
    gatt_connected_after_seconds: float = 0.0
    trainer_ready_after_seconds: float = 0.0
    control_ready_after_seconds: float = 0.0
    first_ftms_after_seconds: float = 0.0
    heart_rate_connected_after_seconds: float = 0.0
    first_heart_rate_after_seconds: float = 0.0
    bluetooth_generation: int = 0
    bluetooth_status: str = "IDLE"
    bluetooth_message: str = ""
    selected_preset: int = 5
    applied_preset: int | None = None
    applied_grade_percent: float = 0.0
    brake_button_held: bool = False
    position_x_meters: float = 0.0
    position_y_meters: float = 0.0
    heading_degrees: float = 0.0
    effective_steering_degrees: float = 0.0
    distance_meters: float = 0.0
    laps_completed: int = 0
    recovery_trail: list[tuple[float, float, float, float]] = field(
        default_factory=list
    )
    recovery_path_distance_meters: float = 0.0
    last_recovery_sample_meters: float = 0.0
    last_recovered_meters: float = 0.0
    last_start_action: str = "IDLE"
    speed_kmh: float = 0.0
    ftms_speed_kmh: float = 0.0
    cadence_rpm: float = 0.0
    power_watts: int = 0
    last_ftms_sample_seconds: float = 0.0
    wheel_signal_received: bool = False
    wheel_revolutions: int | None = None
    wheel_event_time_ticks: int | None = None
    last_wheel_motion_seconds: float = 0.0
    wheel_period_seconds: float = 0.0
    heart_rate_bpm: int | None = None
    heart_rate_status: str = "DISCONNECTED"
    last_heart_rate_sample_seconds: float = 0.0
    ending: bool = False

    def prepare_devices(self) -> bool:
        if self.bluetooth.running:
            self.bluetooth_generation = self.bluetooth.generation
            return False

        self.speed_kmh = 0.0
        self.ftms_speed_kmh = 0.0
        self.cadence_rpm = 0.0
        self.power_watts = 0
        self.last_ftms_sample_seconds = 0.0
        self.wheel_signal_received = False
        self.wheel_revolutions = None
        self.wheel_event_time_ticks = None
        self.last_wheel_motion_seconds = 0.0
        self.wheel_period_seconds = 0.0
        self.heart_rate_bpm = None
        self.heart_rate_status = "SEARCHING"
        self.applied_preset = None
        self.applied_grade_percent = 0.0
        self.bluetooth_status = "SEARCHING"
        self.bluetooth_message = "Searching for CYCPLUS T2"
        self.connection_started_at_seconds = time.monotonic()
        self.bluetooth_generation = self.bluetooth.start(
            self.selected_preset,
            c.BRAKE_GRADE_PERCENT if self.brake_button_held else 0.0,
        )
        self.trainer_found_after_seconds = 0.0
        self.gatt_connected_after_seconds = 0.0
        self.trainer_ready_after_seconds = 0.0
        self.control_ready_after_seconds = 0.0
        self.first_ftms_after_seconds = 0.0
        self.heart_rate_connected_after_seconds = 0.0
        self.first_heart_rate_after_seconds = 0.0
        return True

    def start_ride(self) -> bool:
        if self.ride_active:
            self.last_recovered_meters = self.recover_two_meters()
            self.last_start_action = "SAFETY_RETURN"
            return False
        self.prepare_devices()
        self.ride_started_at_seconds = time.monotonic()
        self.first_motion_after_seconds = 0.0
        if self.brake_button_held and self.bluetooth.running:
            self.bluetooth.request_grade(c.BRAKE_GRADE_PERCENT)
        self.reset_recovery_trail()
        self.last_recovered_meters = 0.0
        self.last_start_action = "STARTED"
        self.ride_active = True
        return True

    def connection_elapsed(self, received_at: float) -> float:
        baseline = self.connection_started_at_seconds or self.ride_started_at_seconds
        return max(0.0, received_at - baseline)

    def set_brake_button_held(self, held: bool) -> None:
        if self.brake_button_held == held:
            return
        self.brake_button_held = held
        if self.ride_active and self.bluetooth.running:
            self.bluetooth.request_grade(c.BRAKE_GRADE_PERCENT if held else 0.0)
            self.bluetooth_status = "SETTING BRAKE" if held else "RELEASING BRAKE"

    def handle_csc_sample(self, received_at: float, sample: CscSample) -> None:
        if sample.wheel_revolutions is None or sample.wheel_event_time_ticks is None:
            return
        previous_revolutions = self.wheel_revolutions
        previous_ticks = self.wheel_event_time_ticks
        self.wheel_signal_received = True
        self.wheel_revolutions = sample.wheel_revolutions
        self.wheel_event_time_ticks = sample.wheel_event_time_ticks
        if previous_revolutions is None or previous_ticks is None:
            self.last_wheel_motion_seconds = received_at
            return

        revolution_delta = (sample.wheel_revolutions - previous_revolutions) & 0xFFFFFFFF
        if revolution_delta == 0:
            return
        tick_delta = (sample.wheel_event_time_ticks - previous_ticks) & 0xFFFF
        if tick_delta > 0 and revolution_delta < 1000:
            period = tick_delta / 1024.0 / revolution_delta
            if 0.01 <= period <= 30.0:
                self.wheel_period_seconds = period
        self.last_wheel_motion_seconds = received_at

    def handle_bluetooth_event(self, event: BluetoothEvent) -> None:
        if event.generation != self.bluetooth_generation:
            return
        if event.type is BluetoothEventType.STATUS:
            self.bluetooth_status = (
                "CONNECTING" if event.message.startswith("CONNECTING:") else "SEARCHING"
            )
            self.bluetooth_message = event.message
            if (
                self.bluetooth_status == "CONNECTING"
                and self.trainer_found_after_seconds <= 0.0
            ):
                self.trainer_found_after_seconds = max(
                    0.0, self.connection_elapsed(event.received_at)
                )
        elif event.type is BluetoothEventType.GATT_CONNECTED:
            self.bluetooth_status = "GATT CONNECTED"
            self.bluetooth_message = event.message
            self.gatt_connected_after_seconds = self.connection_elapsed(
                event.received_at
            )
        elif event.type is BluetoothEventType.TRAINER_READY:
            self.bluetooth_status = "DATA READY"
            self.bluetooth_message = event.message
            self.trainer_ready_after_seconds = self.connection_elapsed(event.received_at)
        elif event.type is BluetoothEventType.CONNECTED:
            self.bluetooth_status = "CONNECTED"
            self.bluetooth_message = "T2 speed data active"
        elif event.type is BluetoothEventType.CONTROL_READY:
            self.applied_preset = event.preset_index
            self.applied_grade_percent = event.grade_percent or 0.0
            self.bluetooth_status = (
                f"BRAKE {self.applied_grade_percent:.1f}% P{event.preset_index}"
                if self.applied_grade_percent > 0.0
                else f"FLAT P{event.preset_index}"
            )
            self.control_ready_after_seconds = self.connection_elapsed(event.received_at)
        elif event.type is BluetoothEventType.CONTROL_UNAVAILABLE:
            self.bluetooth_status = "DATA ONLY"
            self.bluetooth_message = event.message
        elif event.type is BluetoothEventType.TRAINER_SAMPLE:
            sample = event.trainer_sample
            if sample is not None:
                if self.first_ftms_after_seconds <= 0.0:
                    self.first_ftms_after_seconds = self.connection_elapsed(
                        event.received_at
                    )
                if sample.speed_kmh is not None:
                    self.ftms_speed_kmh = max(0.0, sample.speed_kmh)
                if sample.cadence_rpm is not None:
                    self.cadence_rpm = max(0.0, sample.cadence_rpm)
                if sample.power_watts is not None:
                    self.power_watts = max(0, sample.power_watts)
                self.last_ftms_sample_seconds = event.received_at
        elif event.type is BluetoothEventType.CSC_SAMPLE:
            if event.csc_sample is not None:
                self.handle_csc_sample(event.received_at, event.csc_sample)
        elif event.type is BluetoothEventType.CSC_UNAVAILABLE:
            self.bluetooth_message = event.message
        elif event.type is BluetoothEventType.HEART_RATE_CONNECTED:
            self.heart_rate_status = event.message
            self.heart_rate_connected_after_seconds = self.connection_elapsed(
                event.received_at
            )
        elif event.type is BluetoothEventType.HEART_RATE_SAMPLE:
            self.heart_rate_bpm = event.heart_rate_bpm
            self.heart_rate_status = "CONNECTED"
            self.last_heart_rate_sample_seconds = event.received_at
            if self.first_heart_rate_after_seconds <= 0.0:
                self.first_heart_rate_after_seconds = self.connection_elapsed(
                    event.received_at
                )
        elif event.type is BluetoothEventType.HEART_RATE_UNAVAILABLE:
            self.heart_rate_bpm = None
            self.heart_rate_status = event.message
            self.last_heart_rate_sample_seconds = 0.0
        elif event.type is BluetoothEventType.ERROR:
            self.bluetooth_status = "ERROR"
            self.bluetooth_message = event.message
            self.speed_kmh = 0.0
            self.ftms_speed_kmh = 0.0
            self.applied_preset = None
            self.applied_grade_percent = 0.0
            self.ride_active = False
        elif event.type is BluetoothEventType.WORKER_STOPPED:
            if self.bluetooth_status != "ERROR":
                self.bluetooth_status = "IDLE"
                self.bluetooth_message = "Trainer stopped"
            self.ride_active = False

    def update_sensor_state(self, now: float) -> None:
        self.speed_kmh = effective_speed_kmh(
            now,
            self.last_ftms_sample_seconds,
            self.ftms_speed_kmh,
            self.cadence_rpm,
            self.wheel_signal_received,
            self.last_wheel_motion_seconds,
            self.wheel_period_seconds,
        )
        if (
            self.heart_rate_bpm is not None
            and now - self.last_heart_rate_sample_seconds > c.HEART_RATE_STALE_SECONDS
        ):
            self.heart_rate_bpm = None
            self.heart_rate_status = "STALE - SEARCHING"

    def advance_ground(self, delta_seconds: float) -> float:
        if not self.ride_active:
            return 0.0
        advance = self.speed_kmh / 3.6 * max(0.0, min(0.25, delta_seconds))
        if advance <= 0.0:
            return 0.0
        steering = math.radians(self.effective_steering_degrees)
        turn = advance / c.WHEELBASE_METERS * math.tan(steering)
        midpoint_heading = math.radians(self.heading_degrees) + turn * 0.5
        # OpenXR's calibrated forward direction in this scene is Blender Y-.
        self.position_x_meters += math.sin(midpoint_heading) * advance
        self.position_y_meters -= math.cos(midpoint_heading) * advance
        self.heading_degrees = _unwind_degrees(
            self.heading_degrees + math.degrees(turn)
        )
        self.distance_meters += advance
        self.laps_completed = int(
            self.distance_meters // max(1.0, c.DEFAULT_LAP_LENGTH_METERS)
        )
        self.record_recovery_pose(advance)
        return advance

    def reset_recovery_trail(self) -> None:
        self.recovery_path_distance_meters = 0.0
        self.last_recovery_sample_meters = 0.0
        self.recovery_trail = [
            (
                0.0,
                self.position_x_meters,
                self.position_y_meters,
                self.heading_degrees,
            )
        ]

    def record_recovery_pose(self, advance_meters: float) -> None:
        self.recovery_path_distance_meters += max(0.0, advance_meters)
        if (
            self.recovery_path_distance_meters - self.last_recovery_sample_meters
            < 0.1
        ):
            return
        self.recovery_trail.append(
            (
                self.recovery_path_distance_meters,
                self.position_x_meters,
                self.position_y_meters,
                self.heading_degrees,
            )
        )
        self.last_recovery_sample_meters = self.recovery_path_distance_meters
        del self.recovery_trail[:-256]

    def recover_two_meters(self) -> float:
        if not self.recovery_trail:
            self.reset_recovery_trail()
        target_distance = max(0.0, self.recovery_path_distance_meters - 2.0)
        target_pose = self.recovery_trail[0]
        for pose in self.recovery_trail:
            if pose[0] > target_distance:
                break
            target_pose = pose
        recovered = max(0.0, self.recovery_path_distance_meters - target_pose[0])
        _, self.position_x_meters, self.position_y_meters, self.heading_degrees = (
            target_pose
        )
        self.reset_recovery_trail()
        return recovered

    def move_manual(self, direction: float) -> None:
        heading = math.radians(self.heading_degrees)
        distance = direction * c.DEFAULT_MOVE_STEP_METERS
        self.position_x_meters += math.sin(heading) * distance
        self.position_y_meters -= math.cos(heading) * distance

    def turn_manual(self, direction: float) -> None:
        self.heading_degrees = _unwind_degrees(
            self.heading_degrees + direction * c.DEFAULT_TURN_STEP_DEGREES
        )

    def stop_services(self) -> None:
        if not self.bluetooth.stop():
            print("ARRIETTY_BLUETOOTH_STOP_TIMEOUT", flush=True)
        self.ride_active = False
        self.speed_kmh = 0.0
        self.fan.stop()
        if not self.serial.stop():
            print("ARRIETTY_CONTROLLER_STOP_TIMEOUT", flush=True)


_state: RuntimeState | None = None


def _unwind_degrees(value: float) -> float:
    result = math.fmod(value, 360.0)
    if result > 180.0:
        result -= 360.0
    elif result < -180.0:
        result += 360.0
    return result


def _sync_xr_navigation(runtime: RuntimeState) -> None:
    """Apply the ride transform to Blender's persistent OpenXR viewpoint."""
    try:
        import bpy
        from mathutils import Quaternion

        xr_state = bpy.context.window_manager.xr_session_state
        xr_state.navigation_location = (
            runtime.position_x_meters,
            runtime.position_y_meters,
            runtime.flight.altitude_meters,
        )
        heading = math.radians(runtime.heading_degrees) * 0.5
        xr_state.navigation_rotation = Quaternion(
            (math.cos(heading), 0.0, 0.0, math.sin(heading))
        )
    except (AttributeError, RuntimeError):
        # Desktop-only runs do not have an active XR session state.
        pass


def _reset_xr_navigation() -> None:
    try:
        import bpy

        xr_state = bpy.context.window_manager.xr_session_state
        xr_state.navigation_location = (0.0, 0.0, 0.0)
        xr_state.navigation_rotation = (1.0, 0.0, 0.0, 0.0)
    except (AttributeError, RuntimeError):
        pass


def reset() -> RuntimeState:
    global _state
    _state = RuntimeState()
    return _state


def state() -> RuntimeState:
    return _state if _state is not None else reset()


def tick(controller) -> None:
    """Logic-brick module function called once per game tick."""
    runtime = state()
    owner = controller.owner
    now = time.monotonic()
    delta = max(0.0, min(0.25, now - runtime.previous_tick_at))
    runtime.previous_tick_at = now
    runtime.frame_count += 1

    if runtime.frame_count == 1:
        owner["arrietty_status"] = "RUNNING"
        owner["arrietty_version"] = c.VERSION
        owner["controller_status"] = "STARTING"
        owner["controller_pressed_latch"] = 0
        owner["controller_released_latch"] = 0
        owner["controller_transition_count"] = 0
        owner["controller_last_transition"] = ""
        owner["controller_history"] = ""
        owner["ride_active"] = False
        owner["bluetooth_status"] = "IDLE"
        owner["heart_rate_status"] = "DISCONNECTED"
        runtime.fan.start()
        runtime.serial.start()
        if runtime.prepare_devices():
            print("ARRIETTY_BLUETOOTH_PREPARING", flush=True)
        print("ARRIETTY_UP_RUNTIME_READY", flush=True)

    owner["controller_pressed"] = 0
    owner["controller_released"] = 0
    for event in runtime.serial.drain_events():
        if event.message:
            owner["controller_status"] = event.message
            print(f"ARRIETTY_CONTROLLER {event.message}", flush=True)
        if event.type is ControllerEventType.CONNECTED:
            owner["controller_port"] = event.port
        elif event.type is ControllerEventType.DISCONNECTED:
            owner["controller_port"] = ""
        elif event.type is ControllerEventType.SAMPLE and event.sample is not None:
            sample = event.sample
            runtime.controller_button_mask = sample.button_mask
            runtime.set_brake_button_held(bool(sample.button_mask & 0x20))
            runtime.controller_sample_count += 1
            if sample.button_mask:
                runtime.controller_nonzero_samples += 1
            owner["controller_sequence"] = sample.sequence
            owner["controller_j1_x"] = sample.joystick1[0]
            owner["controller_j1_y"] = sample.joystick1[1]
            owner["controller_j2_x"] = sample.joystick2[0]
            owner["controller_j2_y"] = sample.joystick2[1]
            owner["controller_buttons"] = sample.button_mask
            transition = runtime.button_edges.update(sample)
            if transition is not None:
                owner["controller_pressed"] |= transition.pressed
                owner["controller_released"] |= transition.released
                entry = (
                    f"seq={transition.sequence} "
                    f"0x{transition.previous:02X}->0x{transition.current:02X} "
                    f"pressed=0x{transition.pressed:02X} "
                    f"released=0x{transition.released:02X}"
                )
                runtime.button_history.append(entry)
                del runtime.button_history[:-16]
                owner["controller_last_transition"] = entry
                owner["controller_history"] = " | ".join(runtime.button_history)
                print(
                    f"ARRIETTY_CONTROLLER_BUTTONS {entry}",
                    flush=True,
                )
                if transition.pressed & 0x01:
                    if runtime.start_ride():
                        print("ARRIETTY_RIDE_START BUTTON1", flush=True)
                    elif runtime.last_start_action == "SAFETY_RETURN":
                        print(
                            "ARRIETTY_SAFETY_RETURN "
                            f"{runtime.last_recovered_meters:.3f}m BUTTON1",
                            flush=True,
                        )
                if (transition.pressed | transition.released) & 0x20:
                    runtime.set_brake_button_held(bool(transition.current & 0x20))

    import bge

    if (
        not runtime.ending
        and bge.logic.keyboard.inputs[bge.events.PAD0].activated
    ):
        if runtime.start_ride():
            print("ARRIETTY_RIDE_START NUMPAD0", flush=True)
        elif runtime.last_start_action == "SAFETY_RETURN":
            print(
                "ARRIETTY_SAFETY_RETURN "
                f"{runtime.last_recovered_meters:.3f}m NUMPAD0",
                flush=True,
            )

    if bge.logic.keyboard.inputs[bge.events.PAD8].activated:
        runtime.move_manual(1.0)
    if bge.logic.keyboard.inputs[bge.events.PAD2].activated:
        runtime.move_manual(-1.0)
    if bge.logic.keyboard.inputs[bge.events.PAD4].activated:
        runtime.turn_manual(1.0)
    if bge.logic.keyboard.inputs[bge.events.PAD6].activated:
        runtime.turn_manual(-1.0)

    if runtime.bluetooth_generation > 0:
        for event in runtime.bluetooth.drain_events():
            had_ftms = runtime.first_ftms_after_seconds > 0.0
            had_heart_rate = runtime.first_heart_rate_after_seconds > 0.0
            runtime.handle_bluetooth_event(event)
            if (
                event.type is BluetoothEventType.TRAINER_SAMPLE
                and not had_ftms
                and runtime.first_ftms_after_seconds > 0.0
            ):
                print(
                    "ARRIETTY_FIRST_FTMS "
                    f"t={runtime.first_ftms_after_seconds:.3f}s",
                    flush=True,
                )
            if (
                event.type is BluetoothEventType.HEART_RATE_SAMPLE
                and not had_heart_rate
                and runtime.first_heart_rate_after_seconds > 0.0
            ):
                print(
                    "ARRIETTY_FIRST_HEART_RATE "
                    f"t={runtime.first_heart_rate_after_seconds:.3f}s",
                    flush=True,
                )
            if event.message:
                print(
                    "ARRIETTY_BLUETOOTH "
                    f"{event.type.value} "
                    f"t={runtime.connection_elapsed(event.received_at):.3f}s: "
                    f"{event.message}",
                    flush=True,
                )
    runtime.update_sensor_state(now)
    advanced = runtime.advance_ground(delta)
    if (
        advanced > 0.0
        and runtime.first_motion_after_seconds <= 0.0
        and runtime.ride_started_at_seconds > 0.0
    ):
        runtime.first_motion_after_seconds = max(
            0.0, now - runtime.ride_started_at_seconds
        )
        print(
            "ARRIETTY_FIRST_MOTION "
            f"t={runtime.first_motion_after_seconds:.3f}s",
            flush=True,
        )

    owner["controller_sample_count"] = runtime.controller_sample_count
    owner["controller_nonzero_samples"] = runtime.controller_nonzero_samples
    owner["controller_pressed_latch"] = runtime.button_edges.pressed_latch
    owner["controller_released_latch"] = runtime.button_edges.released_latch
    owner["controller_transition_count"] = runtime.button_edges.transition_count
    owner["ride_active"] = runtime.ride_active
    owner["bluetooth_status"] = runtime.bluetooth_status
    owner["bluetooth_message"] = runtime.bluetooth_message
    owner["trainer_found_after_seconds"] = runtime.trainer_found_after_seconds
    owner["gatt_connected_after_seconds"] = runtime.gatt_connected_after_seconds
    owner["trainer_ready_after_seconds"] = runtime.trainer_ready_after_seconds
    owner["control_ready_after_seconds"] = runtime.control_ready_after_seconds
    owner["first_ftms_after_seconds"] = runtime.first_ftms_after_seconds
    owner["first_motion_after_seconds"] = runtime.first_motion_after_seconds
    owner["heart_rate_connected_after_seconds"] = (
        runtime.heart_rate_connected_after_seconds
    )
    owner["first_heart_rate_after_seconds"] = runtime.first_heart_rate_after_seconds
    owner["selected_preset"] = runtime.selected_preset
    owner["applied_preset"] = -1 if runtime.applied_preset is None else runtime.applied_preset
    owner["applied_grade_percent"] = runtime.applied_grade_percent
    owner["speed_kmh"] = runtime.speed_kmh
    owner["ftms_speed_kmh"] = runtime.ftms_speed_kmh
    owner["cadence_rpm"] = runtime.cadence_rpm
    owner["power_watts"] = runtime.power_watts
    owner["heart_rate_bpm"] = -1 if runtime.heart_rate_bpm is None else runtime.heart_rate_bpm
    owner["heart_rate_status"] = runtime.heart_rate_status
    owner["position_x_meters"] = runtime.position_x_meters
    owner["position_y_meters"] = runtime.position_y_meters
    owner["heading_degrees"] = runtime.heading_degrees
    owner["distance_meters"] = runtime.distance_meters
    owner["laps_completed"] = runtime.laps_completed
    owner["last_recovered_meters"] = runtime.last_recovered_meters
    owner.worldPosition = (
        runtime.position_x_meters,
        runtime.position_y_meters,
        runtime.flight.altitude_meters,
    )
    from mathutils import Euler

    owner.worldOrientation = Euler(
        (0.0, 0.0, math.radians(runtime.heading_degrees)), "XYZ"
    ).to_matrix()
    _sync_xr_navigation(runtime)
    runtime.fan.tick(runtime.speed_kmh if runtime.ride_active else 0.0, now)
    owner["fan_status"] = runtime.fan.status
    owner["fan_requested_level"] = runtime.fan.requested_level
    owner["fan_reported_level"] = (
        -1 if runtime.fan.reported_level is None else runtime.fan.reported_level
    )

    owner["arrietty_frames"] = runtime.frame_count
    owner["arrietty_delta_ms"] = round(delta * 1000.0, 3)
    update_upbge_panel(bge.logic.getCurrentScene(), runtime, delta)

    # The scene disables UPBGE's immediate exit key so worker threads can stop
    # before the engine tears down the Python runtime.
    if (
        not runtime.ending
        and bge.logic.keyboard.inputs[bge.events.ESCKEY].activated
    ):
        runtime.ending = True
        owner["arrietty_status"] = "STOPPING"
        runtime.stop_services()
        _reset_xr_navigation()
        print("ARRIETTY_UP_RUNTIME_STOPPED", flush=True)
        bge.logic.endGame()


def shutdown() -> None:
    """Release runtime services before a game session is restarted."""
    global _state
    if _state is not None:
        _state.stop_services()
    _state = None
