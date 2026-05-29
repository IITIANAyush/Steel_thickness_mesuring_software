import numpy as np
import json
from datetime import datetime


class MasteringEngine:

    def __init__(self):
        self.d_baseline = None

    def master_from_frames(
        self,
        top_frames,
        bottom_frames,
        known_thickness,
        output_file='calibration/current.json'
    ):

        z_top = []
        z_bottom = []

        for frame in top_frames:
            z_top.extend(frame.z)

        for frame in bottom_frames:
            z_bottom.extend(frame.z)

        mean_z_top = np.mean(z_top)
        mean_z_bottom = np.mean(z_bottom)

        d_baseline = (
            known_thickness
            + mean_z_top
            + mean_z_bottom
        )

        self.d_baseline = d_baseline

        calibration = {
            'calibration_date': datetime.utcnow().isoformat(),
            'master_thickness_mm': known_thickness,
            'mean_z_top_mm': float(mean_z_top),
            'mean_z_bottom_mm': float(mean_z_bottom),
            'd_baseline_mm': float(d_baseline),
            'std_dev_mm': float(np.std(z_top + z_bottom))
        }

        with open(output_file, 'w') as f:
            json.dump(calibration, f, indent=4)

        return calibration