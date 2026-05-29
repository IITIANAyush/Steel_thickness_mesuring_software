from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import numpy as np


@dataclass
class Frame:
    """Raw 2D profile from one sensor (x-z cross-section at a given encoder position)."""
    x: np.ndarray
    z: np.ndarray
    timestamp: float
    encoder: float          # mm along conveyor
    sensor_id: int = 0      # 0 = top, 1 = bottom


@dataclass
class SensorFrame:
    """Single scalar reading from one sensor (legacy pipeline compatibility)."""
    timestamp: datetime
    sensor_id: int
    raw_value: float
    encoder_position: float


@dataclass
class ProfilePair:
    """Aligned top + bottom profile pair at one encoder position."""
    x_common: np.ndarray
    z_top: np.ndarray
    z_bottom: np.ndarray
    encoder_position: float
    timestamp: float
    slice_index: int = 0


@dataclass
class MeasurementResult:
    """Final per-slice measurement output."""
    encoder_position: float   # mm
    timestamp: float
    thickness_profile: np.ndarray    # per-point thickness across width
    thickness_mean: float            # µm
    thickness_min: float
    thickness_max: float
    thickness_std: float
    sheet_present: bool
    slice_index: int = 0


@dataclass
class SheetResult:
    """Summary for a complete sheet measurement."""
    sheet_id: int
    entry_encoder: float      # mm
    exit_encoder: float       # mm
    length_mm: float
    thickness_mean: float
    thickness_min: float
    thickness_max: float
    thickness_std: float
    n_slices: int
    timestamp: float
