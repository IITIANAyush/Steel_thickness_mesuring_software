import json
from pathlib import Path


class CalibrationIO:
    def __init__(self, calibration_dir):
        self.calibration_dir = Path(calibration_dir)
        self.calibration_dir.mkdir(parents=True, exist_ok=True)

    def save(self, calibration_name, calibration_data):
        path = self.calibration_dir / f"{calibration_name}.json"

        with open(path, "w") as f:
            json.dump(calibration_data, f, indent=4)

        return path

    def load(self, calibration_name):
        path = self.calibration_dir / f"{calibration_name}.json"

        if not path.exists():
            raise FileNotFoundError(f"Calibration file not found: {path}")

        with open(path, "r") as f:
            return json.load(f)