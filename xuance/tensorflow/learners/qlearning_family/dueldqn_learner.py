"""
DQN with Dueling network (Dueling DQN)
Paper link: http://proceedings.mlr.press/v48/wangf16.pdf
Implementation: TensorFlow2
"""
import numpy as np
from argparse import Namespace
from xuance.tensorflow import tf, tk, Module
from xuance.tensorflow.learners import Learner


class DuelDQN_Learner(Learner):
    def __init__(self,
                 config: Namespace,
                 policy: Module):
        super(DuelDQN_Learner, self).__init__(config, policy)
        if ("macOS" in self.os_name) and ("arm" in self.os_name):  # For macOS with Apple's M-series chips.
            self.optimizer = tk.optimizers.legacy.Adam(config.learning_rate)
        else:
            self.optimizer = tk.optimizers.Adam(config.learning_rate)
        self.gamma = config.gamma
        self.sync_frequency = config.sync_frequency

    @tf.function
    def learn(self, obs_batch, act_batch, next_batch, rew_batch, ter_batch):
        with tf.GradientTape() as tape:
            _, _, evalQ = self.policy(obs_batch)
            _, _, targetQ = self.policy.target(next_batch)
            targetQ = tf.reduce_max(targetQ, axis=-1)
            targetQ = rew_batch + self.gamma * (1 - ter_batch) * targetQ
            targetQ = tf.stop_gradient(targetQ)
            predictQ = tf.math.reduce_sum(evalQ * tf.one_hot(act_batch, evalQ.shape[1]), axis=-1)

            loss = tk.losses.mean_squared_error(targetQ, predictQ)
            gradients = tape.gradient(loss, self.policy.trainable_variables)
            self.optimizer.apply_gradients([
                (grad, var)
                for (grad, var) in zip(gradients, self.policy.trainable_variables)
                if grad is not None
            ])
        return predictQ, loss

    def update(self, **samples):
        self.iterations += 1
        obs_batch = samples['obs']
        act_batch = samples['actions'].astype(np.int32)
        next_batch = samples['obs_next']
        rew_batch = samples['rewards']
        ter_batch = samples['terminals']
        predictQ, loss = self.learn(obs_batch, act_batch, next_batch, rew_batch, ter_batch)
        if self.iterations % self.sync_frequency == 0:
            self.policy.copy_target()

        info = {
            "Qloss": loss.numpy(),
            "predictQ": tf.math.reduce_mean(predictQ).numpy(),
        }
        return info
