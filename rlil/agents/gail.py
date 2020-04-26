import torch
from rlil.initializer import get_device, get_writer, get_replay_buffer
from rlil import nn
from .base import Agent


class GAIL(Agent):
    """
    Generative adversarial imitation learning (GAIL)

    GAIL is composed of two neural networks, the policy (generator) network 
    and the discriminator network. In the original paper (https://arxiv.org/abs/1606.03476),
    the policy network is trained using TRPO.
    Since GAIL can be applicable to any policy update algorithms, 
    the implementation in rlil is combined with off-policy algorithms,
    such as ddpg or td3.

    Args:
        base_agent (rlil.agent.Agent): 
            An off-policy agent such as ddpg, td3, sac
        minibatch_size (int): 
            The number of experiences to sample in each discriminator update.
        replay_start_size (int): Number of experiences in replay buffer when training begins.
        update_frequency (int): Number of base_agent update per discriminator update
    """

    def __init__(self,
                 base_agent,
                 minibatch_size=32,
                 replay_start_size=5000,
                 update_frequency=10,
                 ):
        # objects
        self.base_agent = base_agent
        self.replay_buffer = get_replay_buffer()
        # replace base_agent's replay_buffer with gail_buffer
        self.base_agent.replay_buffer = self.replay_buffer
        self.discriminator = self.replay_buffer.discriminator
        self.writer = get_writer()
        self.device = get_device()
        self.discrim_criterion = nn.BCELoss()
        # hyperparameters
        self.minibatch_size = minibatch_size
        self.replay_start_size = replay_start_size
        self.update_frequency = update_frequency

    def act(self, *args, **kwargs):
        return self.base_agent.act(*args, **kwargs)

    def train(self):
        # train discriminator
        if self._should_train():
            samples, expert_samples = self.replay_buffer.sample_both(
                self.minibatch_size)
            states, actions, _, _, _ = samples
            exp_states, exp_actions, _, _, _ = expert_samples

            fake = self.discriminator(
                torch.cat((states.features, actions.features), dim=1))
            real = self.discriminator(
                torch.cat((exp_states.features, exp_actions.features), dim=1))
            discrim_loss = self.discrim_criterion(fake, torch.ones_like(fake)) + \
                self.discrim_criterion(real, torch.zeros_like(real))
            self.discriminator.reinforce(discrim_loss)

            # additional debugging info
            self.writer.add_scalar('gail/fake', fake.mean())
            self.writer.add_scalar('gail/real', real.mean())

        # train base_agent
        self.base_agent.train()

    def _should_train(self):
        return len(self.replay_buffer) > self.replay_start_size and \
            self.writer.train_steps % self.update_frequency == 0

    def make_lazy_agent(self, *args, **kwargs):
        return self.base_agent.make_lazy_agent(*args, **kwargs)

    def load(self, dirname):
        self.agent.load(dirname)
