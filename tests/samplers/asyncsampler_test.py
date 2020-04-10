import pytest
import numpy as np
import torch
import gym
import time
import warnings
import ray
from rlil import nn
from rlil.environments import GymEnvironment, Action
from rlil.policies.deterministic import DeterministicPolicyNetwork
from rlil.samplers import AsyncSampler
from rlil.memory import ExperienceReplayBuffer
from rlil.initializer import set_replay_buffer
from ..mock_agent import MockAgent


@pytest.fixture()
def setUp():
    ray.init(include_webui=False, ignore_reinit_error=True)

    replay_buffer_size = 100
    replay_buffer = ExperienceReplayBuffer(replay_buffer_size)
    set_replay_buffer(replay_buffer)

    env = GymEnvironment('LunarLanderContinuous-v2')
    agent = MockAgent(env)

    yield {"env": env, "agent": agent}


def test_sampler_episode(setUp):
    env = setUp["env"]
    agent = setUp["agent"]

    num_workers = 3
    worker_episodes = 6
    sampler = AsyncSampler(
        env,
        num_workers=num_workers,
    )
    lazy_agent = agent.make_lazy_agent()
    sampler.start_sampling(
        lazy_agent, worker_episodes=worker_episodes)
    sample_info = sampler.store_samples(timeout=1e8)

    # GIVEN the store_samples function with infinite timeout
    # WHEN worker_episodes are specified
    # THEN sampler collects samples by the num of num_workers * worker_episodes
    assert sample_info["episodes"] == num_workers * worker_episodes


def test_sampler_frames(setUp):
    env = setUp["env"]
    agent = setUp["agent"]

    num_workers = 3
    worker_frames = 50
    sampler = AsyncSampler(
        env,
        num_workers=num_workers,
    )

    lazy_agent = agent.make_lazy_agent()
    sampler.start_sampling(
        lazy_agent, worker_frames=worker_frames)
    sample_info = sampler.store_samples(timeout=1e8)

    # GIVEN the store_samples function with infinite timeout
    # WHEN worker_frames are specified
    # THEN sampler collects samples until frames exceeds worker_frames * num_workers
    assert sample_info["frames"] > worker_frames * num_workers


def test_ray_wait(setUp):
    env = setUp["env"]
    agent = setUp["agent"]
    sampler = AsyncSampler(
        env,
        num_workers=3,
    )

    worker_episodes = 100
    lazy_agent = agent.make_lazy_agent()
    sampler.start_sampling(
        lazy_agent, worker_episodes=worker_episodes)
    sampler.store_samples(timeout=0.1)

    # GIVEN the store_samples function with short timeout
    # WHEN worker_episodes is large
    # THEN sampler doesn't wait the worker finishes sampling
    assert len(sampler._replay_buffer) == 0
