import math
import unittest

from voxdrive.voxdrive_voice.maneuver import VoiceManeuverController


class VoiceManeuverControllerTest(unittest.TestCase):
    def test_lane_change_is_followed_by_centering_and_release(self):
        controller = VoiceManeuverController(
            lane_change_max_distance_m=18.0,
            lane_change_settle_distance_m=3.0,
            lane_change_min_lateral_m=2.5,
        )
        controller.submit("CHANGE_LEFT", (0.0, 0.0), 0.0)

        self.assertEqual(controller.update((-1.0, -1.0), math.radians(5.0)), 5)
        self.assertEqual(controller.update((-2.6, -6.0), math.radians(1.0)), 4)
        self.assertEqual(controller.snapshot()["phase"], "settling")

        self.assertEqual(controller.update((-2.8, -8.0), 0.0), 4)
        self.assertIsNone(controller.update((-3.0, -9.0), 0.0))
        self.assertTrue(controller.snapshot()["just_completed"])

    def test_lane_change_does_not_finish_after_heading_only_swerve(self):
        controller = VoiceManeuverController(
            lane_change_max_distance_m=18.0,
            lane_change_min_lateral_m=2.5,
        )
        controller.submit("CHANGE_LEFT", (0.0, 0.0), 0.0)

        self.assertEqual(controller.update((-0.5, -1.0), math.radians(5.0)), 5)
        self.assertEqual(controller.update((-0.5, -6.0), math.radians(1.0)), 5)
        self.assertEqual(controller.snapshot()["phase"], "active")
        self.assertLess(controller.snapshot()["lateral_progress_m"], 2.5)

    def test_right_lane_change_uses_opposite_lateral_direction(self):
        controller = VoiceManeuverController(lane_change_min_lateral_m=2.5)
        controller.submit("CHANGE_RIGHT", (0.0, 0.0), 0.0)

        self.assertEqual(controller.update((1.0, -1.0), math.radians(5.0)), 6)
        self.assertEqual(controller.update((2.6, -6.0), math.radians(1.0)), 4)
        self.assertEqual(controller.snapshot()["phase"], "settling")

    def test_distance_turn_waits_before_overriding_route(self):
        controller = VoiceManeuverController()
        controller.submit(
            "TURN_RIGHT_AFTER_DISTANCE",
            (0.0, 0.0),
            0.0,
            delay_distance_m=10.0,
        )

        self.assertIsNone(controller.update((4.0, 0.0), 0.0))
        self.assertIsNone(controller.update((9.0, 0.0), 0.0))
        self.assertEqual(controller.update((10.0, 0.0), 0.0), 2)

    def test_turn_switches_to_lane_follow_after_heading_change(self):
        controller = VoiceManeuverController(turn_settle_distance_m=2.0)
        controller.submit("TURN_LEFT_NEXT", (0.0, 0.0), 0.0)

        self.assertEqual(controller.update((3.0, 0.0), math.radians(30.0)), 1)
        self.assertEqual(controller.update((6.0, 0.0), math.radians(55.0)), 4)
        self.assertEqual(controller.snapshot()["phase"], "settling")


if __name__ == "__main__":
    unittest.main()
