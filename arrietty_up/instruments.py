"""Instrument-panel formatting and UPBGE display updates.

The formatting and attitude calculations stay Blender-independent so that the
panel can be exercised without the bicycle, HMD, or UPBGE runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


PITCH_METERS_PER_DEGREE = 0.004


@dataclass(frozen=True, slots=True)
class InstrumentReadout:
    heart_rate: str
    trainer_power: str
    ground_speed: str
    trainer_grade: str
    mode: str
    airspeed: str
    airspeed_ticks: tuple[str, str, str, str]
    altitude: str
    altitude_ticks: tuple[str, str, str, str]
    physics: str
    debug: str


def _mode(runtime) -> str:
    if runtime.flight_enabled:
        return "FLIGHT" if runtime.flight.airborne else "FLIGHT ARMED"
    if runtime.ride_active:
        return "RIDE"
    return "STANDBY"


def _tape_ticks(value: float, step: float, *, decimals: int = 0) -> tuple[str, ...]:
    center = round(value / step) * step
    formatter = f"{{:.{decimals}f}}"
    values = (center - 2 * step, center - step, center + step, center + 2 * step)
    return tuple("" if item < 0.0 else formatter.format(item) for item in values)


def build_readout(runtime, delta_seconds: float) -> InstrumentReadout:
    """Create all changing panel strings from a runtime-like object."""
    flight = runtime.flight
    airspeed_kmh = max(0.0, flight.airspeed_meters_per_second * 3.6)
    altitude_meters = max(0.0, flight.altitude_meters)
    heart_rate = "---" if runtime.heart_rate_bpm is None else str(runtime.heart_rate_bpm)
    grade = (
        "--.- %"
        if runtime.applied_preset is None
        else f"{runtime.applied_grade_percent:4.1f} %"
    )
    reported_fan = "--" if runtime.fan.reported_level is None else str(runtime.fan.reported_level)
    ground_speed = getattr(runtime, "ground_speed_kmh", runtime.speed_kmh)
    steering_status = getattr(runtime, "steering_status", "IDLE")
    steering_degrees = getattr(runtime, "effective_steering_degrees", 0.0)
    command_pitch = getattr(runtime.digital_controls, "pitch_degrees", 0.0)
    command_roll = getattr(runtime.digital_controls, "roll_right_degrees", 0.0)
    tuning_status = runtime.tuning_controls.compact_status()
    if runtime.tuning_controls.active:
        tuning_status = tuning_status.replace("TUNE ", "T", 1)
    physics = "\n".join(
        (
            f"V/S    {flight.vertical_speed_meters_per_second:+5.1f} m/s",
            f"PITCH  {flight.pitch_degrees:+5.1f} deg",
            f"BANK   {flight.bank_degrees:+5.1f} deg",
            f"AOA    {flight.angle_of_attack_degrees:+5.1f} deg",
            f"CAD    {runtime.cadence_rpm:5.1f} rpm",
            f"HEAD   {runtime.heading_degrees:+5.1f} deg",
        )
    )
    debug = "\n".join(
        (
            f"T2  {runtime.bluetooth_status}",
            f"HR  {runtime.heart_rate_status}",
            f"STR {steering_status} {steering_degrees:+.1f}",
            f"CMD P{command_pitch:+.0f} R{command_roll:+.0f}",
            tuning_status,
            f"FAN {runtime.fan.requested_level}/{reported_fan}",
            f"VOICE {getattr(runtime, 'voice_status', 'IDLE')}",
            f"FRAME {max(0.0, delta_seconds) * 1000.0:4.1f} ms",
        )
    )
    return InstrumentReadout(
        heart_rate=heart_rate,
        trainer_power=str(max(0, runtime.power_watts)),
        ground_speed=f"{max(0.0, ground_speed):4.1f} km/h",
        trainer_grade=grade,
        mode=_mode(runtime),
        airspeed=f"{airspeed_kmh:.0f}",
        airspeed_ticks=_tape_ticks(airspeed_kmh, 10.0),
        altitude=f"{altitude_meters:.0f}",
        altitude_ticks=_tape_ticks(altitude_meters, 50.0),
        physics=physics,
        debug=debug,
    )


def attitude_transform(
    pitch_degrees: float,
    bank_degrees: float,
    pitch_scale: float = PITCH_METERS_PER_DEGREE,
) -> tuple[float, float, float]:
    """Return horizon X/Z shift and in-panel rotation in degrees.

    Pitch translation is rotated with the horizon so the pitch ladder remains
    rigidly attached to it during a bank.
    """
    pitch = max(-30.0, min(30.0, pitch_degrees))
    rotation_degrees = -bank_degrees
    rotation = math.radians(rotation_degrees)
    unbanked_z = -pitch * pitch_scale
    return (
        math.sin(rotation) * unbanked_z,
        math.cos(rotation) * unbanked_z,
        rotation_degrees,
    )


def _scene_object(scene, name: str):
    try:
        return scene.objects[name]
    except (KeyError, SystemError):
        return None


def _set_text(scene, name: str, value: str) -> None:
    obj = _scene_object(scene, name)
    if obj is not None and obj.get("Text") != value:
        obj["Text"] = value


def update_upbge_panel(scene, runtime, delta_seconds: float) -> None:
    """Update authored font objects and the moving PFD horizon."""
    readout = build_readout(runtime, delta_seconds)
    fields = {
        "Instrument_HeartRateValue": readout.heart_rate,
        "Instrument_PowerValue": readout.trainer_power,
        "Instrument_GroundSpeedValue": readout.ground_speed,
        "Instrument_GradeValue": readout.trainer_grade,
        "Instrument_ModeValue": readout.mode,
        "Instrument_AirspeedValue": readout.airspeed,
        "Instrument_AltitudeValue": readout.altitude,
        "Instrument_PhysicsText": readout.physics,
        "Instrument_DebugText": readout.debug,
    }
    for name, value in fields.items():
        _set_text(scene, name, value)

    for suffix, value in zip(("M2", "M1", "P1", "P2"), readout.airspeed_ticks):
        _set_text(scene, f"Instrument_AirspeedTick_{suffix}", value)
    for suffix, value in zip(("M2", "M1", "P1", "P2"), readout.altitude_ticks):
        _set_text(scene, f"Instrument_AltitudeTick_{suffix}", value)

    horizon = _scene_object(scene, "Instrument_PFD_Horizon")
    if horizon is not None:
        from mathutils import Matrix

        _, _, rotation = attitude_transform(
            runtime.flight.pitch_degrees,
            runtime.flight.bank_degrees,
        )
        horizon.localPosition = (0.0, horizon.get("panel_base_y", 0.018), 0.0)
        horizon.localOrientation = Matrix.Rotation(
            math.radians(rotation), 3, "Y"
        )
        ladder = _scene_object(scene, "Instrument_PFD_Ladder")
        if ladder is not None:
            pitch = max(-30.0, min(30.0, runtime.flight.pitch_degrees))
            ladder.localPosition = (
                0.0,
                ladder.get("panel_base_y", 0.005),
                -pitch * PITCH_METERS_PER_DEGREE,
            )
