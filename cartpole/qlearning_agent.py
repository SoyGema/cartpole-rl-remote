from collections import deque
import numpy as np
import random
import abc

from seldon.seldon_client import SeldonClient


class QLearningAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size

        # hyperparameters
        self.gamma = 0.95  # discount rate on future rewards
        self.epsilon = 1.0  # exploration rate
        self.epsilon_decay = 0.995  # the decay of epsilon after each training batch
        self.epsilon_min = 0.1  # the minimum exploration rate permissible
        self.batch_size = 32  # maximum size of the batches sampled from memory

        # agent state
        self.model = self.build_model()
        self.memory = deque(maxlen=2000)
        self.seldon_client = None

    @abc.abstractmethod
    def build_model(self):
        return None

    def select_action(self, state, train=None, host=None):
        random_exploit = np.random.rand()
        if train and random_exploit <= self.epsilon:
            return random.randrange(self.action_size), None, None
        elif train and random_exploit > self.epsilon:
            return np.argmax(self.model.predict(state)[0]), None, None
        else:
            print('Calling remote model...')
            if not self.seldon_client:
                self.seldon_client = SeldonClient(host)

            request, response = self.seldon_client.rest_request(state)

            return int(response.get('data').get('tensor').get('values')[0]), request, response

    def record(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def replay(self):
        if len(self.memory) < self.batch_size:
            return 0

        minibatch = random.sample(self.memory, self.batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                target = (reward + self.gamma *
                          np.amax(self.model.predict(next_state)[0]))
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
