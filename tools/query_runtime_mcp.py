"""Return one compact UPBGE runtime snapshot through Blender MCP."""

from arrietty_up import runtime


state = runtime.state()
result = {
    "version": __import__("arrietty_up.constants", fromlist=["VERSION"]).VERSION,
    "generation": state.bluetooth_generation,
    "worker_running": state.bluetooth.running,
    "ride_active": state.ride_active,
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
    "fan_status": state.fan.status,
}
