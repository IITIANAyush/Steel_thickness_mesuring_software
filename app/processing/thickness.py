import numpy as np


# ---------------------------------------------------------------------------
# Dual-sensor thickness formula (same-rail reference geometry):
#   Both sensors measure Z distance from the same rail baseline.
#   thickness(x) = Z_bottom(x) - Z_top(x)
#
# d_calibration stores the mean reference thickness (Z_bot_mean - Z_top_mean)
# from the calibration CSV, but the per-point formula does not use it —
# variation is captured directly from the Z difference at each point.
# ---------------------------------------------------------------------------

class ThicknessCalculator:
    """Per-point thickness across a cross-section profile."""

    def __init__(self, d_calibration: float):
        """
        d_calibration: mean reference thickness (mm) = mean(Z_bottom) - mean(Z_top)
                       derived from calibration CSV profiles.
        """
        self.d_calibration = d_calibration

    def compute_profile(self, z_top: np.ndarray, z_bottom: np.ndarray) -> np.ndarray:
        """Compute per-point thickness array (mm). Clipped to >= 0."""
        thickness = z_bottom - z_top
        return np.clip(thickness, 0.0, None)

    def compute_mean(self, z_top: np.ndarray, z_bottom: np.ndarray) -> float:
        return float(np.mean(self.compute_profile(z_top, z_bottom)))


def compute_thickness(z_top, z_bottom, d_calibration=None):
    """
    Standalone function: same-rail thickness at one point or over arrays.
    d_calibration is accepted for API compatibility but not used.
    """
    result = np.asarray(z_bottom) - np.asarray(z_top)
    if np.ndim(result) == 0:
        return max(float(result), 0.0)
    return np.clip(result, 0.0, None)
