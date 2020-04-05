import ray
import numpy as np
import os
import torch
from rlil.initializer import get_replay_buffer
from rlil.environments import State, Action
from rlil.samplers import Sampler


# TODO: LazyAgent class with replay_buffer

@ray.remote
class Worker:
    def __init__(self, make_env, seed):
        self.seed = seed
        np.random.seed(seed)
        torch.manual_seed(seed)

        self._env = make_env()
        self._env.seed(seed)
        self._frames = 0
        self._episodes = 0

        print("Worker initialized in PID: {}".format(os.getpid()))

    def frames(self):
        return self._frames

    def episodes(self):
        return self._episodes

    def sample(self, lazy_agent, max_frames, max_episodes):

        self._frames = 0
        self._episodes = 0

        while self._frames < max_frames and self._episodes < max_episodes:
            self._env.reset()
            action = lazy_agent.act(self._env.state, self._env.reward)

            while not self._env.done:
                self._env.step(action)
                self._frames += 1
                action = lazy_agent.act(self._env.state, self._env.reward)

            self._episodes += 1

        return (State.from_list(lazy_agent.buffer["states"]),
                Action.from_list(lazy_agent.buffer["actions"]),
                torch.tensor(lazy_agent.buffer["rewards"], dtype=torch.float),
                State.from_list(lazy_agent.buffer["next_states"]))


class AsyncSampler(Sampler):
    """
    AsyncSampler collects samples with asynchronous workers.
    All the workers have the same agent, which is given by the argument
    of the start_sampling method.

    Args:
        Sampler ([type]): [description]
    """

    def __init__(
            self,
            env,
            num_workers=1,
            seed=0,
    ):
        self._env = env
        self._workers = [Worker.remote(env.duplicate, seed+i)
                         for i in range(num_workers)]
        self._work_ids = {worker: None for worker in self._workers}
        self._replay_buffer = get_replay_buffer()

    def start_sampling(self,
                       lazy_agent,
                       max_frames=np.inf,
                       max_episodes=np.inf):

        assert max_frames != np.inf or max_episodes != np.inf, \
            "max_frames or max_episodes must be specified"

        # start sample method if the worker is ready
        for worker in self._workers:
            if self._work_ids[worker] is None:
                self._work_ids[worker] = \
                    worker.sample.remote(lazy_agent, max_frames, max_episodes)

    def store_samples(self, timeout=0.1):
        # store samples if the worker finishes sampling
        for worker, _id in self._work_ids.items():
            ready_id, remaining_id = \
                ray.wait([_id], num_returns=1, timeout=timeout)

            if len(ready_id) > 0:
                self._replay_buffer.store(*ray.get(ready_id[0]))