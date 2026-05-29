class AcquisitionPipeline:
    def __init__(self, sensor_manager, threading_model):
        self.sensor_manager = sensor_manager
        self.threading_model = threading_model

    def start(self):
        self.sensor_manager.register_callback(self._frame_callback)
        self.sensor_manager.start()

    def stop(self):
        self.sensor_manager.stop()

    def _frame_callback(self, frame):
        self.threading_model.raw_queue.put(frame)