import time
import signal
import sys

from app.pipeline.threading_model import ThreadingModel
from app.pipeline.acquisition_pipeline import AcquisitionPipeline
from app.pipeline.processing_pipeline import ProcessingPipeline

from app.sensors.sensor_manager import SensorManager
from app.sensors.encoder_manager import EncoderManager
from app.sensors.simulation_loader import SimulationLoader


from app.export.csv_logger import CSVLogger
from app.visualization.live_plot import LivePlot



class SteelThicknessApplication:
    def __init__(self):

        self.running = True

        # Core threading model
        self.threading_model = ThreadingModel()
        # Encoder
        self.encoder_manager = EncoderManager()

        # Sensors
        self.sensor_manager = SensorManager(
            encoder_manager=self.encoder_manager,
            sensor_count=2,
            sample_rate=100
        )

        # Logger
        self.logger = CSVLogger("logs/thickness_log.csv")

        # Pipelines
        self.acquisition_pipeline = AcquisitionPipeline(
            sensor_manager=self.sensor_manager,
            threading_model=self.threading_model
        )

        self.processing_pipeline = ProcessingPipeline(
            threading_model=self.threading_model,
            logger=self.logger
        )

        # Visualization
        self.live_plot = LivePlot()

    def start(self):

        print("Starting Steel Thickness System...")

        self.encoder_manager.start()

        self.acquisition_pipeline.start()

        self.processing_pipeline.start()

        while self.running:

            processed_frame = self.threading_model.processed_queue.get()

            self.live_plot.update(
                processed_frame.encoder_position,
                processed_frame.thickness
            )

    def stop(self):

        print("Stopping system...")

        self.running = False

        self.acquisition_pipeline.stop()

        self.processing_pipeline.stop()

        self.sensor_manager.stop()

        self.encoder_manager.stop()

        self.logger.close()


def signal_handler(sig, frame):
    global app
    app.stop()
    sys.exit(0)


if __name__ == '__main__':

    app = SteelThicknessApplication()

    signal.signal(signal.SIGINT, signal_handler)

    app.start()