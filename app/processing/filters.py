import numpy as np
from collections import deque


class MovingAverageFilter:
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.buffer = deque(maxlen=window_size)

    def apply(self, value):
        self.buffer.append(value)
        return float(np.mean(self.buffer))


class MedianFilter:
    def __init__(self, window_size=5):
        self.buffer = deque(maxlen=window_size)

    def apply(self, value):
        self.buffer.append(value)
        return float(np.median(self.buffer))


class ExponentialFilter:
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.state = None

    def apply(self, value):
        if self.state is None:
            self.state = value
        else:
            self.state = self.alpha * value + (1 - self.alpha) * self.state

        return self.state