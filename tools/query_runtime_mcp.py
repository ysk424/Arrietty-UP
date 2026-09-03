"""Return one compact UPBGE runtime snapshot through Blender MCP."""

from arrietty_up import runtime


state = runtime.state()
result = {
    "version": __import__("arrietty_up.constants", fromlist=["VERSION"]).VERSION,
    "frame_count": state.frame_count,
    "generation": state.bluetooth_generation,
    "worker_running": state.bluetooth.running,
    "ride_active": state.ride_active,
    "ride_elapsed_seconds": round(state.ride_elapsed_seconds, 3),
    "hmd_aligned": state.hmd_aligned,
    "hmd_alignment_degrees": round(state.hmd_alignment_degrees, 3),
    "hmd_alignment_message": state.hmd_alignment_message,
    "flight_enabled": state.flight_enabled,
    "flight_airborne": state.flight.airborne,
    "flight_stalled": state.flight.stalled,
    "flight_event": state.last_flight_event,
    "flight_command_pitch_degrees": state.digital_controls.pitch_degrees,
    "flight_command_bank_degrees": state.digital_controls.bank_degrees,
    "flight_pitch_degrees": round(state.flight.pitch_degrees, 3),
    "flight_bank_degrees": round(state.flight.bank_degrees, 3),
    "altitude_meters": round(state.flight.altitude_meters, 3),
    "vertical_speed_mps": round(
        state.flight.vertical_speed_meters_per_second, 3
    ),
    "propulsion_power_watts": round(state.propulsion_power_watts, 3),
    "bluetooth_status": state.bluetooth_status,
    "bluetooth_message": state.bluetooth_message,
    "trainer_found_after_seconds": round(state.trainer_found_after_seconds, 3),
    "gatt_connected_after_seconds": round(
        getattr(state, "gatt_connected_after_seconds", 0.0), 3
    ),
    "trainer_ready_after_seconds": round(
        getattr(state, "trainer_ready_after_seconds", 0.0), 3
    ),
    "first_ftms_after_seconds": round(state.first_ftms_after_seconds, 3),
    "first_motion_after_seconds": round(
        getattr(state, "first_motion_after_seconds", 0.0), 3
    ),
    "control_ready_after_seconds": round(state.control_ready_after_seconds, 3),
    "heart_rate_connected_after_seconds": round(
        getattr(state, "heart_rate_connected_after_seconds", 0.0), 3
    ),
    "first_heart_rate_after_seconds": round(
        getattr(state, "first_heart_rate_after_seconds", 0.0), 3
    ),
    "speed_kmh": round(state.speed_kmh, 3),
    "ground_speed_kmh": round(state.ground_speed_kmh, 3),
    "cadence_rpm": round(state.cadence_rpm, 3),
    "power_watts": state.power_watts,
    "heart_rate_status": state.heart_rate_status,
    "heart_rate_bpm": state.heart_rate_bpm,
    "distance_meters": round(state.distance_meters, 3),
    "last_recovered_meters": round(
        getattr(state, "last_recovered_meters", 0.0), 3
    ),
    "position": [
        round(state.position_x_meters, 3),
        round(state.position_y_meters, 3),
    ],
    "heading_degrees": round(state.heading_degrees, 3),
    "steering_tracking": state.steering_tracking,
    "steering_status": state.steering_status,
    "steering_message": state.steering_message,
    "raw_steering_degrees": round(state.raw_steering_degrees, 3),
    "effective_steering_degrees": round(state.effective_steering_degrees, 3),
    "controller_button_mask": state.controller_button_mask,
    "joystick1": [round(value, 3) for value in state.joystick1_axes],
    "joystick2": [round(value, 3) for value in state.joystick2_axes],
    "control_message": state.last_control_message,
    "tuning": state.tuning_controls.compact_status(),
    "ptt_held": state.ptt_held,
    "voice_status": state.voice_status,
    "voice_detail": state.voice.detail,
    "fan_status": state.fan.status,
    "fan_connected": state.fan.connected,
    "fan_apparent_speed_kmh": round(state.fan_apparent_speed_kmh(), 3),
    "fan_requested_level": state.fan.requested_level,
    "fan_reported_level": state.fan.reported_level,
    "fan_packets_sent": state.fan.packets_sent,
    "fan_packets_received": state.fan.packets_received,
    "fan_invalid_responses": state.fan.invalid_responses,
}
