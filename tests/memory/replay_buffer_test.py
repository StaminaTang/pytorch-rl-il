import unittest
import random
import torch
import numpy as np
import gym
import torch_testing as tt
from rlil.environments import State, Action
from rlil.memory import (
    ExperienceReplayBuffer,
    PrioritizedReplayBuffer,
    NStepReplayBuffer,
)
from rlil.initializer import set_device


class TestExperienceReplayBuffer(unittest.TestCase):
    def setUp(self):
        np.random.seed(1)
        random.seed(1)
        torch.manual_seed(1)
        set_device(torch.device("cpu"))
        self.replay_buffer = ExperienceReplayBuffer(5)

    def test_run(self):
        states = torch.arange(0, 20, dtype=torch.float).view((-1, 1))
        Action.set_action_space(gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(1, )))
        actions = torch.arange(0, 20).view((-1, 1))
        rewards = torch.arange(0, 20, dtype=torch.float)
        expected_samples = torch.tensor(
            [
                [0, 0, 0],
                [1, 1, 0],
                [0, 1, 1],
                [3, 0, 0],
                [1, 4, 4],
                [1, 2, 4],
                [2, 4, 3],
                [4, 7, 4],
                [7, 4, 6],
                [6, 5, 6],
            ]
        )
        expected_weights = np.ones((10, 3))
        actual_samples = []
        actual_weights = []
        for i in range(10):
            state = State(states[i].view(1, -1), torch.tensor([1]).bool())
            next_state = State(
                states[i + 1].view(1, -1), torch.tensor([1]).bool())
            action = Action(actions[i].view(1, -1))
            self.replay_buffer.store(
                state, action, rewards[i].unsqueeze(0), next_state)
            sample = self.replay_buffer.sample(3)
            actual_samples.append(sample[0].features)
            actual_weights.append(sample[-1])
        tt.assert_equal(
            torch.cat(actual_samples).view(
                expected_samples.shape), expected_samples
        )
        np.testing.assert_array_equal(
            expected_weights, np.vstack(actual_weights))

    def test_multi_store(self):
        states = torch.arange(0, 5, dtype=torch.float).view((-1, 1))
        Action.set_action_space(gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(1, )))
        actions = torch.arange(0, 5).view((-1, 1)).float()
        rewards = torch.arange(0, 5, dtype=torch.float)
        expected_samples = torch.tensor(
            [
                [1, 3, 0],
                [0, 3, 1],
            ]
        )
        expected_weights = np.ones((2, 3))

        actual_samples = []
        actual_weights = []
        states = State(states)
        actions = Action(actions)
        self.replay_buffer.store(states[:-1], actions, rewards, states[1:])
        for i in range(2):
            sample = self.replay_buffer.sample(3)
            actual_samples.append(sample[0].features)
            actual_weights.append(sample[-1])
        tt.assert_equal(
            torch.cat(actual_samples).view(
                expected_samples.shape), expected_samples
        )
        np.testing.assert_array_equal(
            expected_weights, np.vstack(actual_weights))


class TestPrioritizedReplayBuffer(unittest.TestCase):
    def setUp(self):
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        set_device(torch.device("cpu"))
        self.replay_buffer = PrioritizedReplayBuffer(5, 0.6)

    def test_run(self):
        states = State(torch.arange(0, 20, dtype=torch.float).view(-1, 1))
        Action.set_action_space(gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(1, )))
        actions = Action(torch.arange(0, 20).view((-1, 1)))
        rewards = torch.arange(0, 20, dtype=torch.float)
        expected_samples = State(
            torch.FloatTensor(
                [
                    [0, 1, 2],
                    [0, 1, 3],
                    [5, 5, 5],
                    [6, 6, 2],
                    [7, 7, 7],
                    [7, 8, 8],
                    [7, 7, 7],
                ]
            )
        )
        expected_weights = [
            [1.0000, 1.0000, 1.0000],
            [0.5659, 0.7036, 0.5124],
            [0.0631, 0.0631, 0.0631],
            [0.0631, 0.0631, 0.1231],
            [0.0631, 0.0631, 0.0631],
            [0.0776, 0.0631, 0.0631],
            [0.0866, 0.0866, 0.0866],
        ]
        actual_samples = []
        actual_weights = []
        for i in range(10):
            self.replay_buffer.store(
                states[i], actions[i], rewards[i].unsqueeze(0), states[i + 1])
            if i > 2:
                sample = self.replay_buffer.sample(3)
                sample_states = sample[0].features
                self.replay_buffer.update_priorities(torch.randn(3))
                actual_samples.append(sample_states)
                actual_weights.append(sample[-1])

        actual_samples = State(torch.cat(actual_samples).view((-1, 3)).float())
        self.assert_states_equal(actual_samples, expected_samples)
        np.testing.assert_array_almost_equal(
            expected_weights, np.vstack(actual_weights), decimal=3
        )

    def test_multi_store(self):
        Action.set_action_space(gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(1, )))
        states = torch.arange(0, 5, dtype=torch.float).view((-1, 1))
        actions = torch.arange(0, 5).view((-1, 1))
        rewards = torch.arange(0, 5, dtype=torch.float)
        expected_samples = torch.tensor(
            [
                [0, 1, 2],
                [0, 0, 1],
            ]
        )
        expected_weights = torch.tensor(
            [
                [1, 1, 1],
                [0.565882, 0.565882, 0.703553]
            ]
        )

        actual_samples = []
        actual_weights = []
        states = State(states)
        actions = Action(actions)
        self.replay_buffer.store(states[:-1], actions, rewards, states[1:])
        for _ in range(2):
            sample = self.replay_buffer.sample(3)
            self.replay_buffer.update_priorities(torch.randn(3))
            actual_samples.append(sample[0].features)
            actual_weights.append(sample[-1])
        tt.assert_equal(
            torch.cat(actual_samples).view(
                expected_samples.shape), expected_samples
        )
        np.testing.assert_almost_equal(
            expected_weights, np.vstack(actual_weights), decimal=5)

    def assert_states_equal(self, actual, expected):
        tt.assert_almost_equal(actual.raw, expected.raw)
        tt.assert_equal(actual.mask, expected.mask)


class TestNStepReplayBuffer(unittest.TestCase):
    def setUp(self):
        np.random.seed(1)
        random.seed(1)
        torch.manual_seed(1)
        set_device(torch.device("cpu"))
        self.replay_buffer = NStepReplayBuffer(
            4, 0.5, ExperienceReplayBuffer(100))

    def test_run(self):
        states = State(torch.arange(0, 20, dtype=torch.float).view(-1, 1))
        Action.set_action_space(gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(1, )))
        actions = Action(torch.arange(0, 20).view(-1, 1))
        rewards = torch.arange(0, 20, dtype=torch.float)

        for i in range(3):
            self.replay_buffer.store(
                states[i], actions[i], rewards[i].unsqueeze(0), states[i + 1])
            self.assertEqual(len(self.replay_buffer), 0)

        for i in range(3, 6):
            self.replay_buffer.store(
                states[i], actions[i], rewards[i].unsqueeze(0), states[i + 1])
            self.assertEqual(len(self.replay_buffer), i - 2)

        sample = self.replay_buffer.buffer.buffer[0]
        self.assert_states_equal(sample[0], states[0])
        tt.assert_equal(sample[1].raw, actions[0].raw)
        tt.assert_equal(sample[2], torch.tensor(
            0 + 1 * 0.5 + 2 * 0.25 + 3 * 0.125))
        tt.assert_equal(
            self.replay_buffer.buffer.buffer[1][2],
            torch.tensor(1 + 2 * 0.5 + 3 * 0.25 + 4 * 0.125),
        )

    def test_done(self):
        state = State(torch.FloatTensor([1]).view(1, -1))
        Action.set_action_space(gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(1, )))
        action = Action(torch.tensor(0).view(1, -1))
        reward = torch.FloatTensor([1])
        done_state = State(torch.FloatTensor([1]).view(
            1, -1), mask=torch.tensor([0]).bool())

        self.replay_buffer.store(state, action, reward, done_state)
        self.assertEqual(len(self.replay_buffer), 1)
        sample = self.replay_buffer.buffer.buffer[0]
        self.assert_states_equal(state, sample[0])
        self.assertEqual(sample[2], 1)

        self.replay_buffer.store(state, action, reward, state)
        self.replay_buffer.store(state, action, reward, state)
        self.assertEqual(len(self.replay_buffer), 1)

        self.replay_buffer.store(state, action, reward, done_state)
        self.assertEqual(len(self.replay_buffer), 4)
        sample = self.replay_buffer.buffer.buffer[1]
        self.assert_states_equal(sample[0], state)
        self.assertEqual(sample[2], 1.75)
        self.assert_states_equal(sample[3], done_state)

        self.replay_buffer.store(state, action, reward, done_state)
        self.assertEqual(len(self.replay_buffer), 5)
        sample = self.replay_buffer.buffer.buffer[0]
        self.assert_states_equal(state, sample[0])
        self.assertEqual(sample[2], 1)

    def assert_states_equal(self, actual, expected):
        tt.assert_almost_equal(actual.raw, expected.raw)
        tt.assert_equal(actual.mask, expected.mask)


if __name__ == "__main__":
    unittest.main()
