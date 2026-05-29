import threading

from app.processing.filters import MovingAverageFilter
from app.processing.thickness import compute_thickness
from app.sensors.frame import ProcessedFrame


class ProcessingPipeline:
    def __init__(self, threading_model, logger=None):
        self.threading_model = threading_model
        self.logger = logger
        self.running = False

        self.filter = MovingAverageFilter(window_size=5)

    def start(self):
        self.running = True
        threading.Thread(target=self._processing_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _processing_loop(self):
        while self.running:
            frame = self.threading_model.raw_queue.get()

            filtered = self.filter.apply(frame.raw_value)
            thickness = compute_thickness(filtered)

            processed = ProcessedFrame(
                timestamp=frame.timestamp,
                sensor_id=frame.sensor_id,
                filtered_value=filtered,
                thickness=thickness,
                encoder_position=frame.encoder_position,
            )

            self.threading_model.processed_queue.put(processed)

            if self.logger:
                self.logger.log(
                    frame.timestamp,
                    frame.sensor_id,
                    frame.raw_value,
                    filtered,
                    thickness,
                )