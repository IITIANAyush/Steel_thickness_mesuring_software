import random
import threading
import time
from datetime import datetime

from app.sensors.frame import SensorFrame


class SensorManager:
    def __init__(self, encoder_manager, sensor_count=2, sample_rate=100):
        self.encoder_manager = encoder_manager
        self.sensor_count = sensor_count
        self.sample_rate = sample_rate
        self.running = False
        self.callbacks = []

    def register_callback(self, callback):
        self.callbacks.append(callback)

    def start(self):
        self.running = True
        threading.Thread(target=self._acquisition_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _acquisition_loop(self):
        period = 1.0 / self.sample_rate

        while self.running:
            encoder_pos = self.encoder_manager.get_position()

            for sensor_id in range(self.sensor_count):
                value = 10 + random.uniform(-0.5, 0.5)

                frame = SensorFrame(
                    timestamp=datetime.utcnow(),
                    sensor_id=sensor_id,
                    raw_value=value,
                    encoder_position=encoder_pos,
                )

                for callback in self.callbacks:
                    callback(frame)

            time.sleep(period)