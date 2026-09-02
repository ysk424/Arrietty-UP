import unittest

from arrietty_up.instruments import attitude_transform, build_readout
from arrietty_up.runtime import RuntimeState


class InstrumentTests(unittest.TestCase):
    def test_ground_panel_formats_live_and_unavailable_values(self):
        state = RuntimeState()
        state.ride_active = True
        state.heart_rate_bpm = 87
        state.power_watts = 214
        state.speed_kmh = 23.45
        state.ground_speed_kmh = 23.45
        state.applied_preset = 5
        state.applied_grade_percent = 3.0
        state.cadence_rpm = 81.25

        panel = build_readout(state, 1.0 / 60.0)

        self.assertEqual(panel.heart_rate, "87")
        self.assertEqual(panel.trainer_power, "214")
        self.assertEqual(panel.ground_speed, "23.4 km/h")
        self.assertEqual(panel.trainer_grade, " 3.0 %")
        self.assertEqual(panel.mode, "RIDE")
        self.assertIn("CAD     81.2 rpm", panel.physics)
        self.assertIn("STR IDLE +0.0", panel.debug)
        self.assertIn("CMD P+0 R+0", panel.debug)
        self.assertIn("FRAME 16.7 ms", panel.debug)

    def test_unavailable_grade_and_heart_rate_are_not_shown_as_zero(self):
        panel = build_readout(RuntimeState(), 0.0)

        self.assertEqual(panel.heart_rate, "---")
        self.assertEqual(panel.trainer_grade, "--.- %")
        self.assertEqual(panel.mode, "STANDBY")

    def test_flight_tapes_and_mode_use_flight_state(self):
        state = RuntimeState()
        state.flight_enabled = True
        state.flight.airborne = True
        state.flight.airspeed_meters_per_second = 12.5
        state.flight.altitude_meters = 123.0

        panel = build_readout(state, 0.01)

        self.assertEqual(panel.mode, "FLIGHT")
        self.assertEqual(panel.airspeed, "45")
        self.assertEqual(panel.airspeed_ticks, ("20", "30", "50", "60"))
        self.assertEqual(panel.altitude, "123")
        self.assertEqual(panel.altitude_ticks, ("0", "50", "150", "200"))

    def test_pitch_ladder_translation_rotates_with_horizon(self):
        x, z, roll = attitude_transform(10.0, 0.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(z, -0.04)
        self.assertEqual(roll, 0.0)

        x, z, roll = attitude_transform(10.0, 90.0)
        self.assertAlmostEqual(x, 0.04)
        self.assertAlmostEqual(z, 0.0, places=7)
        self.assertEqual(roll, -90.0)

    def test_pfd_pitch_translation_is_bounded(self):
        self.assertEqual(attitude_transform(1000.0, 0.0), (0.0, -0.12, 0.0))


if __name__ == "__main__":
    unittest.main()
