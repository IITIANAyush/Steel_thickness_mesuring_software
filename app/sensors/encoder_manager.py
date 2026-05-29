import threading
import time
import random


class EncoderManager:
    def __init__(self, resolution=4096):
        self.resolution = resolution
        self.position = 0.0
        self.velocity = 0.0
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        threading.Thread(target=self._update_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _update_loop(self):
        while self.running:
            with self.lock:
                delta = random.uniform(0.01, 0.1)
                self.position += delta
                self.velocity = delta * 100
            time.sleep(0.01)

    def get_position(self):
        with self.lock:
            return self.position

    def get_velocity(self):
        with self.lock:
            return self.velocity