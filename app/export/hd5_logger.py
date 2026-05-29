from pathlib import Path

import h5py


class HDF5Logger:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.file = h5py.File(self.file_path, "a")

        if "measurements" not in self.file:
            self.dataset = self.file.create_dataset(
                "measurements",
                shape=(0, 5),
                maxshape=(None, 5),
                dtype="f",
                compression="gzip",
            )
        else:
            self.dataset = self.file["measurements"]

    def log(self, timestamp, sensor_id, raw_value, filtered_value, thickness):
        row = [
            float(timestamp.timestamp()),
            sensor_id,
            raw_value,
            filtered_value,
            thickness,
        ]

        self.dataset.resize((self.dataset.shape[0] + 1, 5))
        self.dataset[-1] = row
        self.file.flush()

    def close(self):
        self.file.close()