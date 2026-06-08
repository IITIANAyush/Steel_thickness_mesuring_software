"""
simulation_loader.py — CSV → Frame loader with Y-column support.
If the CSV contains a Y column it is read; otherwise Y defaults to zeros.
"""
import pandas as pd
import numpy as np
import time
from app.sensors.frame import Frame


class SimulationLoader:
    """Loads one CSV scan profile into a Frame (case-insensitive columns)."""

    def load_csv(self, filepath: str, sensor_id: int = 0) -> Frame:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().upper() for c in df.columns]   # normalise X/Y/Z

        x = df['X'].to_numpy(dtype=np.float64)
        z = df['Z'].to_numpy(dtype=np.float64)

        # Y column is optional — present in real 3-D scans, zero in 2-D profiles
        if 'Y' in df.columns:
            y = df['Y'].to_numpy(dtype=np.float64)
        else:
            y = np.zeros_like(x)

        # Sort by X so interpolation works correctly
        order = np.argsort(x)
        x, z, y = x[order], z[order], y[order]

        return Frame(
            x=x,
            z=z,
            y=y,
            timestamp=time.time(),
            encoder=0.0,
            sensor_id=sensor_id,
        )
