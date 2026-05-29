from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


class ReportGenerator:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_csv_report(self, records, filename="report.csv"):
        df = pd.DataFrame(records)
        path = self.output_dir / filename
        df.to_csv(path, index=False)
        return path

    def generate_plot(self, records, filename="thickness_plot.png"):
        df = pd.DataFrame(records)

        plt.figure(figsize=(12, 5))
        plt.plot(df["encoder_position"], df["thickness"])
        plt.xlabel("Encoder Position")
        plt.ylabel("Thickness (mm)")
        plt.title("Thickness Profile")
        plt.grid(True)

        path = self.output_dir / filename
        plt.savefig(path)
        plt.close()

        return path