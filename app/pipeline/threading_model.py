from queue import Queue


class ThreadingModel:
    def __init__(self):
        self.raw_queue = Queue(maxsize=5000)
        self.processed_queue = Queue(maxsize=5000)
        self.visualization_queue = Queue(maxsize=5000)