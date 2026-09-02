import unittest

from arrietty_up.bluetooth import BluetoothEvent, BluetoothEventType
from arrietty_up.models import CscSample, TrainerSample
from arrietty_up.runtime import RuntimeState


class FakeBluetooth:
    def __init__(self):
        self.running = False
        self.generation = 0
        self.start_args = None
        self.grade_requests = []

    def start(self, preset, grade):
        self.running = True
        self.generation += 1
        self.start_args = (preset, grade)
        return self.generation

    def request_grade(self, grade):
        self.grade_requests.append(grade)

    def stop(self, _timeout=5.0):
        self.running = False
        return True


class RuntimeStateTests(unittest.TestCase):
    def make_state(self):
        state = RuntimeState()
        state.bluetooth = FakeBluetooth()
        return state

    def test_start_ride_and_brake_requests(self):
        state = self.make_state()
        self.assertTrue(state.start_ride())
        self.assertEqual(state.bluetooth_generation, 1)
        self.assertEqual(state.bluetooth.start_args, (5, 0.0))
        self.assertTrue(state.ride_active)

        state.set_brake_button_held(True)
        state.set_brake_button_held(True)
        state.set_brake_button_held(False)
        self.assertEqual(state.bluetooth.grade_requests, [3.0, 0.0])

    def test_devices_can_prepare_before_the_ride(self):
        state = self.make_state()
        self.assertTrue(state.prepare_devices())
        self.assertFalse(state.ride_active)
        self.assertEqual(state.bluetooth_generation, 1)
        self.assertFalse(state.prepare_devices())
        self.assertTrue(state.start_ride())
        self.assertTrue(state.ride_active)
        self.assertEqual(state.bluetooth.generation, 1)

    def test_brake_held_during_prepare_is_applied_at_ride_start(self):
        state = self.make_state()
        state.prepare_devices()
        state.set_brake_button_held(True)
        self.assertEqual(state.bluetooth.grade_requests, [])
        state.start_ride()
        self.assertEqual(state.bluetooth.grade_requests, [3.0])

    def test_repeated_start_does_not_claim_connection_is_ready(self):
        state = self.make_state()
        state.start_ride()
        state.bluetooth_status = "CONNECTING"
        state.bluetooth_message = "Connecting to T2"
        self.assertFalse(state.start_ride())
        self.assertEqual(state.bluetooth_status, "CONNECTING")
        self.assertEqual(state.bluetooth_message, "Connecting to T2")

    def test_connection_phase_timings(self):
        state = self.make_state()
        state.start_ride()
        state.connection_started_at_seconds = 90.0
        state.ride_started_at_seconds = 90.0
        state.handle_bluetooth_event(
            BluetoothEvent(
                1,
                BluetoothEventType.GATT_CONNECTED,
                "GATT connected",
                received_at=100.0,
            )
        )
        state.handle_bluetooth_event(
            BluetoothEvent(
                1,
                BluetoothEventType.TRAINER_READY,
                "T2 speed notifications active",
                received_at=101.5,
            )
        )
        self.assertEqual(state.gatt_connected_after_seconds, 10.0)
        self.assertEqual(state.trainer_ready_after_seconds, 11.5)
        self.assertEqual(state.bluetooth_status, "DATA READY")

    def test_ftms_and_heart_rate_events(self):
        state = self.make_state()
        state.start_ride()
        state.handle_bluetooth_event(
            BluetoothEvent(
                1,
                BluetoothEventType.TRAINER_SAMPLE,
                trainer_sample=TrainerSample(21.5, 82.0, 103),
                received_at=100.0,
            )
        )
        state.handle_bluetooth_event(
            BluetoothEvent(
                1,
                BluetoothEventType.HEART_RATE_SAMPLE,
                heart_rate_bpm=76,
                received_at=100.0,
            )
        )
        state.update_sensor_state(100.1)
        self.assertEqual((state.speed_kmh, state.cadence_rpm, state.power_watts), (21.5, 82.0, 103))
        self.assertEqual(state.heart_rate_bpm, 76)

        state.update_sensor_state(106.0)
        self.assertEqual(state.speed_kmh, 0.0)
        self.assertIsNone(state.heart_rate_bpm)
        self.assertEqual(state.heart_rate_status, "STALE - SEARCHING")

    def test_csc_motion_and_stop_timing(self):
        state = self.make_state()
        state.handle_csc_sample(10.0, CscSample(100, 1000, None, None))
        state.handle_csc_sample(11.0, CscSample(101, 2024, None, None))
        self.assertTrue(state.wheel_signal_received)
        self.assertEqual(state.last_wheel_motion_seconds, 11.0)
        self.assertAlmostEqual(state.wheel_period_seconds, 1.0)

        state.ftms_speed_kmh = 12.0
        state.cadence_rpm = 0.0
        state.last_ftms_sample_seconds = 13.0
        state.update_sensor_state(13.0)
        self.assertEqual(state.speed_kmh, 0.0)

    def test_stale_generation_is_ignored(self):
        state = self.make_state()
        state.start_ride()
        state.handle_bluetooth_event(
            BluetoothEvent(
                0,
                BluetoothEventType.HEART_RATE_SAMPLE,
                heart_rate_bpm=200,
                received_at=100.0,
            )
        )
        self.assertIsNone(state.heart_rate_bpm)

    def test_ground_and_manual_movement_use_openxr_forward(self):
        state = self.make_state()
        state.ride_active = True
        state.speed_kmh = 18.0
        self.assertAlmostEqual(state.advance_ground(0.2), 1.0)
        self.assertAlmostEqual(state.position_x_meters, 0.0)
        self.assertAlmostEqual(state.position_y_meters, -1.0)
        self.assertAlmostEqual(state.distance_meters, 1.0)

        state.move_manual(1.0)
        self.assertAlmostEqual(state.position_y_meters, -1.5)
        state.turn_manual(1.0)
        self.assertAlmostEqual(state.heading_degrees, 5.0)

    def test_second_start_returns_about_two_meters_on_ridden_path(self):
        state = self.make_state()
        state.start_ride()
        state.speed_kmh = 3.6
        for _ in range(30):
            state.advance_ground(0.1)
        distance_before = state.distance_meters

        self.assertFalse(state.start_ride())
        self.assertEqual(state.last_start_action, "SAFETY_RETURN")
        self.assertAlmostEqual(state.last_recovered_meters, 2.0, delta=0.11)
        self.assertAlmostEqual(state.position_y_meters, -1.0, delta=0.11)
        self.assertAlmostEqual(state.distance_meters, distance_before)


if __name__ == "__main__":
    unittest.main()
