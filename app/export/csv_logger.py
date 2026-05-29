import csv
from pathlib import Path


class CSVLogger:

    def __init__(self, filepath):
        self.filepath = Path(filepath)

    def log(
        self,
        timestamp,
        encoder,
        x,
        thickness
    ):

        file_exists = self.filepath.exists()

        with open(self.filepath, 'a', newline='') as f:
            writer = csv.writer(f)

            if not file_exists:
                header = ['timestamp', 'encoder']
                header += [f'x_{i}' for i in range(len(x))]
                header += [f't_{i}' for i in range(len(thickness))]
                writer.writerow(header)

            row = [timestamp, encoder]
            row += list(x)
            row += list(thickness)

            writer.writerow(row)