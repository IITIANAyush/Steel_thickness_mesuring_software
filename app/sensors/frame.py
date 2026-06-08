"""
frame.py — Data containers for the Steel Thickness Monitor.
Adds y-coordinate support to Frame and ProfilePair for 3-D bend-aware
thickness measurement.
"""
from __future__ import annotations
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
    y: Optional[np.ndarray] = None   # NEW: y-coords (width axis), None = all zeros


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
    x_common:         np.ndarray
    z_top:            np.ndarray
    z_bottom:         np.ndarray
    encoder_position: float
    timestamp:        float
    slice_index:      int = 0
    # ── 3-D extensions ──────────────────────────────────────────────────
    y_common:  Optional[np.ndarray] = None   # Y coords across width (mm)
    bend_disp: Optional[np.ndarray] = None   # actual bend displacement applied (mm)


@dataclass
class MeasurementResult:
    """Final per-slice measurement output."""
    encoder_position:  float
    timestamp:         float
    thickness_profile: np.ndarray   # per-point thickness across width
    thickness_mean:    float
    thickness_min:     float
    thickness_max:     float
    thickness_std:     float
    sheet_present:     bool
    slice_index:       int = 0
    # ── 3-D result extras ───────────────────────────────────────────────
    method:            str = "flat"          # "flat" | "3d_tangent"
    bend_corrected:    bool = False


@dataclass
class SheetResult:
    """Summary for a complete sheet measurement."""
    sheet_id:        int
    entry_encoder:   float
    exit_encoder:    float
    length_mm:       float
    thickness_mean:  float
    thickness_min:   float
    thickness_max:   float
    thickness_std:   float
    n_slices:        int
    timestamp:       float
