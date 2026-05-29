import numpy as np
from collections import deque


class TemporalFilter:

    def __init__(self, history_size=5):
        self.buffer = deque(maxlen=history_size)

    def update(self, signal):
        self.buffer.append(signal)

        stacked = np.stack(self.buffer)

        return np.mean(stacked, axis=0)