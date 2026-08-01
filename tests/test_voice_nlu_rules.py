import unittest

from voxdrive.voxdrive_nlu.intent_parser import VoxDriveNLU


class VoiceNLURulesTest(unittest.TestCase):
    def setUp(self):
        self.parser = VoxDriveNLU(use_embedding=False)
        self.now = 10.0

    def command(self, text):
        self.now += 2.0
        self.parser.parse("命令", now=self.now)
        return self.parser.parse(text, now=self.now + 0.1)

    def test_accelerate(self):
        self.assertEqual(self.command("加速").intent, "ACCELERATE")

    def test_lane_change(self):
        self.assertEqual(self.command("向左变道").intent, "CHANGE_LEFT")

    def test_turn(self):
        self.assertEqual(self.command("下个路口右转").intent, "TURN_RIGHT_NEXT")

    def test_speed_target(self):
        result = self.command("加速到每小时二十公里")
        self.assertEqual(result.intent, "SET_SPEED")
        self.assertEqual(result.speed_limit_kmh, 20.0)


if __name__ == "__main__":
    unittest.main()
