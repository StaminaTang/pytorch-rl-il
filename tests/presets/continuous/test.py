import unittest
from rlil.environments import GymEnvironment
from rlil.presets.validate_agent import validate_agent
from rlil.presets.continuous import ddpg, sac, td3


class TestContinuousPresets(unittest.TestCase):
    def test_ddpg(self):
        self.validate(ddpg(replay_start_size=50))

    def test_sac(self):
        self.validate(sac(replay_start_size=50))

    def test_td3(self):
        self.validate(td3(replay_start_size=50))

    def validate(self, make_agent):
        validate_agent(make_agent, GymEnvironment('LunarLanderContinuous-v2'))


if __name__ == '__main__':
    unittest.main()