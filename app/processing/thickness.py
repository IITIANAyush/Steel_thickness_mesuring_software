import numpy as np


# ---------------------------------------------------------------------------
# Dual-sensor thickness formula (from Pando Data brief):
#   thickness(x) = Z_ref_top(x) - Z_top(x) - (Z_bottom(x) - Z_ref_bottom(x))
# Which simplifies to:
#   thickness(x) = (Z_ref_top + Z_ref_bottom) - Z_top(x) - Z_bottom(x)
#                = D_calibration - Z_top(x) - Z_bottom(x)
# Where D_calibration is established during mastering with a calibration block.
# ---------------------------------------------------------------------------

class ThicknessCalculator:
    """Per-point thickness across a cross-section profile."""

    def __init__(self, d_calibration: float):
        """
        d_calibration: total C-frame gap (mm) = Z_ref_top + Z_ref_bottom
                       measured over a calibration block of known thickness T.
                       d_calibration = mean_Z_top_cal + mean_Z_bot_cal + T_known
        """
        self.d_calibration = d_calibration

    def compute_profile(self, z_top: np.ndarray, z_bottom: np.ndarray) -> np.ndarray:
        """Compute per-point thickness array (mm). Clipped to >= 0."""
        thickness = self.d_calibration - z_top - z_bottom
        return np.clip(thickness, 0.0, None)

    def compute_mean(self, z_top: np.ndarray, z_bottom: np.ndarray) -> float:
        return float(np.mean(self.compute_profile(z_top, z_bottom)))


def compute_thickness(z_top, z_bottom, d_calibration):
    """
    Standalone function: dual-sensor thickness at one point or over arrays.
    Returns scalar or ndarray.
    """
    result = d_calibration - np.asarray(z_top) - np.asarray(z_bottom)
    if np.ndim(result) == 0:
        return max(float(result), 0.0)
    return np.clip(result, 0.0, None)
