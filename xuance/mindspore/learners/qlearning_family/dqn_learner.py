"""
Deep Q-Network (DQN)
Paper link: https://www.nature.com/articles/nature14236
Implementation: MindSpore
"""
from xuance.mindspore import ms, Module, Tensor
from xuance.mindspore.learners import Learner
from argparse import Namespace
from mindspore.ops import OneHot
from mindspore.nn import MSELoss, Adam


class DQN_Learner(Learner):
    def __init__(self,
                 config: Namespace,
                 policy: Module):
        super(DQN_Learner, self).__init__(config, policy)
        self.optimizer = Adam(params=self.policy.trainable_params(), learning_rate=self.config.learning_rate, eps=1e-5)
        self.gamma = config.gamma
        self.sync_frequency = config.sync_frequency
        self.mse_loss = MSELoss()
        self.one_hot = OneHot()
        self.n_actions = self.policy.action_dim
        # Get gradient function
        self.grad_fn = ms.value_and_grad(self.forward_fn, None, self.optimizer.parameters, has_aux=True)
        self.policy.set_train()

    def forward_fn(self, x, a, label):
        _, _, _evalQ = self.policy(x)
        _predict_Q = (_evalQ * self.one_hot(a.astype(ms.int32), _evalQ.shape[1], Tensor(1.0), Tensor(0.0))).sum(
            axis=-1)
        loss = self.mse_loss(_predict_Q, label)
        return loss, _predict_Q

    def update(self, **samples):
        self.iterations += 1
        obs_batch = Tensor(samples['obs'])
        act_batch = Tensor(samples['actions'])
        rew_batch = Tensor(samples['rewards'])
        next_batch = Tensor(samples['obs_next'])
        ter_batch = Tensor(samples['terminals'])

        _, _, evalQ = self.policy(obs_batch)
        _, _, targetQ = self.policy.target(next_batch)
        targetQ = targetQ.max(axis=-1)
        targetQ = rew_batch + self.gamma * (1 - ter_batch) * targetQ

        (loss, predictQ), grads = self.grad_fn(obs_batch, act_batch, targetQ)
        self.optimizer(grads)

        # hard update for target network
        if self.iterations % self.sync_frequency == 0:
            self.policy.copy_target()

        lr = self.scheduler(self.iterations).asnumpy()

        info = {
            "Qloss": loss.asnumpy(),
            "predictQ": predictQ.mean().asnumpy(),
            "learning_rate": lr
        }

        return info
