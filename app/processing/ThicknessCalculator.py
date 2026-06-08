import numpy as np


class ThicknessCalculator:
    """Per-point thickness across a cross-section profile."""

    def __init__(self, d_calibration: float):
        self.d_calibration = d_calibration

    def compute_profile(self, z_top: np.ndarray, z_bottom: np.ndarray) -> np.ndarray:
        """Compute per-point thickness array (mm). Clipped to >= 0."""
        thickness = z_bottom - z_top
        return np.clip(thickness, 0.0, None)

    def compute_mean(self, z_top: np.ndarray, z_bottom: np.ndarray) -> float:
        return float(np.mean(self.compute_profile(z_top, z_bottom)))


def compute_thickness(z_top, z_bottom, d_calibration=None):
    result = np.asarray(z_bottom) - np.asarray(z_top)
    if np.ndim(result) == 0:
        return max(float(result), 0.0)
    return np.clip(result, 0.0, None)
