"""
SimulationEngine
================
Generates a realistic multi-slice sensor dataset from the two template CSV
profiles.  It replays what the real scanCONTROL sensors would stream for a
steel sheet travelling through the C-frame gate.

Geometry (all values in mm unless noted):
  - Top sensor above sheet, reading DOWN  → high Z when no sheet, lower Z when
    sheet surface is present.
  - Bottom sensor below sheet, reading UP → same convention mirrored.
  - D_cal = Z_ref_top + Z_ref_bottom  (total C-frame gap, established during
    mastering on a calibration block of known thickness T_known).
  - Per-point thickness = D_cal - Z_top(x) - Z_bottom(x)

Simulation timeline (encoder positions in mm):
  0 → pre_len   : empty conveyor  (Z ≈ Z_ref, thickness ≈ 0)
  pre_len → pre_len + sheet_len  : steel sheet present
  pre_len + sheet_len → total    : empty conveyor again
"""

import time
import numpy as np
from scipy.interpolate import interp1d
from app.sensors.frame import Frame, ProfilePair, MeasurementResult, SheetResult
from app.sensors.simulation_loader import SimulationLoader
from app.processing.thickness import ThicknessCalculator
from app.processing.alignment import align_profiles
from app.processing.cosine_correction import cosine_correct
from app.processing.statistics import compute_statistics


# ── tuneable simulation parameters ──────────────────────────────────────────
NOMINAL_THICKNESS_MM  = 10.0        # target steel sheet thickness
SHEET_LENGTH_MM       = 4000.0       # simulated sheet length
PRE_BUFFER_MM         = 50.0        # empty conveyor before sheet
POST_BUFFER_MM        = 50.0        # empty conveyor after sheet
ENCODER_STEP_MM       = 2.0         # distance between consecutive slices
SHEET_NOISE_STD       = 0.030       # ±30 µm Gaussian noise on Z readings
TILT_ANGLE_RAD        = 0.003       # small sheet tilt for cosine-correction demo
SHEET_DETECT_Z_DELTA  = 2.0         # Z drop that confirms sheet entry (mm)
N_POINTS              = 512         # resampled cross-section points
# ────────────────────────────────────────────────────────────────────────────


class SimulationEngine:

    def __init__(
        self,
        top_csv: str = "data/top_profile.csv",
        bottom_csv: str = "data/bottom_profile.csv",
    ):
        loader = SimulationLoader()
        self.top_template    = loader.load_csv(top_csv,    sensor_id=0)
        self.bottom_template = loader.load_csv(bottom_csv, sensor_id=1)

        # ── calibration ─────────────────────────────────────────────────────
        # Treat CSV profiles as sheet-surface measurements.
        # Reference values = sheet-surface mean + half nominal thickness each side.
        self._z_ref_top    = float(np.mean(self.top_template.z)    + NOMINAL_THICKNESS_MM / 2)
        self._z_ref_bottom = float(np.mean(self.bottom_template.z) + NOMINAL_THICKNESS_MM / 2)
        self.d_calibration = self._z_ref_top + self._z_ref_bottom   # total C-frame gap

        self.calc = ThicknessCalculator(d_calibration=self.d_calibration)

        # Build interpolators for template profiles (resampled to N_POINTS)
        x_top = self.top_template.x
        x_bot = self.bottom_template.x
        x_min = max(x_top.min(), x_bot.min())
        x_max = min(x_top.max(), x_bot.max())
        self.x_common = np.linspace(x_min, x_max, N_POINTS)

        self._top_interp = interp1d(x_top, self.top_template.z,
                                    kind='linear', fill_value='extrapolate')
        self._bot_interp = interp1d(x_bot, self.bottom_template.z,
                                    kind='linear', fill_value='extrapolate')

        self._z_top_sheet    = self._top_interp(self.x_common)
        self._z_bottom_sheet = self._bot_interp(self.x_common)

        # Air-gap profile (no sheet): sensors read reference values
        self._z_top_air    = np.full(N_POINTS, self._z_ref_top)
        self._z_bottom_air = np.full(N_POINTS, self._z_ref_bottom)

        # Timeline
        total_mm = PRE_BUFFER_MM + SHEET_LENGTH_MM + POST_BUFFER_MM
        self.encoder_positions = np.arange(0.0, total_mm, ENCODER_STEP_MM)
        self.sheet_entry = PRE_BUFFER_MM
        self.sheet_exit  = PRE_BUFFER_MM + SHEET_LENGTH_MM

        # State
        self._rng = np.random.default_rng(42)
        self.calibration_info = {
            "z_ref_top_mm":    round(self._z_ref_top,    3),
            "z_ref_bottom_mm": round(self._z_ref_bottom, 3),
            "d_calibration_mm": round(self.d_calibration, 3),
            "nominal_thickness_mm": NOMINAL_THICKNESS_MM,
        }

    # ── private helpers ──────────────────────────────────────────────────────

    def _make_profile_pair(self, encoder_pos: float, slice_idx: int) -> ProfilePair:
        """Generate a synthetic ProfilePair at the given encoder position."""
        sheet_here = self.sheet_entry <= encoder_pos < self.sheet_exit

        if sheet_here:
            # Slight thickness variation along the sheet (±0.5 mm linear drift + noise)
            rel = (encoder_pos - self.sheet_entry) / SHEET_LENGTH_MM   # 0→1
            drift = 0.5 * np.sin(rel * np.pi)                          # crown shape
            noise_top = self._rng.normal(0, SHEET_NOISE_STD, N_POINTS)
            noise_bot = self._rng.normal(0, SHEET_NOISE_STD, N_POINTS)
            z_top    = self._z_top_sheet    - drift / 2 + noise_top
            z_bottom = self._z_bottom_sheet - drift / 2 + noise_bot
        else:
            # Empty conveyor: Z ≈ reference (tiny noise)
            noise_top = self._rng.normal(0, SHEET_NOISE_STD * 0.5, N_POINTS)
            noise_bot = self._rng.normal(0, SHEET_NOISE_STD * 0.5, N_POINTS)
            z_top    = self._z_top_air    + noise_top
            z_bottom = self._z_bottom_air + noise_bot

        return ProfilePair(
            x_common=self.x_common,
            z_top=z_top,
            z_bottom=z_bottom,
            encoder_position=encoder_pos,
            timestamp=time.time(),
            slice_index=slice_idx,
        )

    def _detect_sheet(self, pair: ProfilePair) -> bool:
        """Z-threshold sheet detection: both sensors must see a Z drop."""
        z_top_mean = float(np.mean(pair.z_top))
        z_bot_mean = float(np.mean(pair.z_bottom))
        top_drop = self._z_ref_top    - z_top_mean
        bot_drop = self._z_ref_bottom - z_bot_mean
        return (top_drop > SHEET_DETECT_Z_DELTA) and (bot_drop > SHEET_DETECT_Z_DELTA)

    def _process_pair(self, pair: ProfilePair, sheet_present: bool) -> MeasurementResult:
        """Compute thickness from a ProfilePair."""
        thickness_profile = self.calc.compute_profile(pair.z_top, pair.z_bottom)
        # Cosine correction for warp
        thickness_profile = cosine_correct(thickness_profile, TILT_ANGLE_RAD)
        stats = compute_statistics(thickness_profile)
        return MeasurementResult(
            encoder_position=pair.encoder_position,
            timestamp=pair.timestamp,
            thickness_profile=thickness_profile,
            thickness_mean=stats['mean'],
            thickness_min=stats['min'],
            thickness_max=stats['max'],
            thickness_std=stats['std'],
            sheet_present=sheet_present,
            slice_index=pair.slice_index,
        )

    # ── public API ───────────────────────────────────────────────────────────

    def run(self, step_delay_s: float = 0.05):
        """
        Generator: yields MeasurementResult one slice at a time.
        At sheet exit also yields a SheetResult summary.
        Caller controls replay speed via step_delay_s.
        """
        sheet_measurements = []
        entry_encoder = None
        sheet_id = 0

        for idx, enc in enumerate(self.encoder_positions):
            pair        = self._make_profile_pair(enc, idx)
            sheet_here  = self._detect_sheet(pair)
            result      = self._process_pair(pair, sheet_here)

            # Sheet entry
            if sheet_here and entry_encoder is None:
                entry_encoder = enc
                sheet_measurements = []

            # Accumulate
            if sheet_here:
                sheet_measurements.append(result)

            # Sheet exit
            if not sheet_here and entry_encoder is not None:
                if sheet_measurements:
                    all_means = [r.thickness_mean for r in sheet_measurements]
                    exit_enc  = enc
                    sr = SheetResult(
                        sheet_id=sheet_id,
                        entry_encoder=entry_encoder,
                        exit_encoder=exit_enc,
                        length_mm=exit_enc - entry_encoder,
                        thickness_mean=float(np.mean(all_means)),
                        thickness_min=float(np.min([r.thickness_min for r in sheet_measurements])),
                        thickness_max=float(np.max([r.thickness_max for r in sheet_measurements])),
                        thickness_std=float(np.std(all_means)),
                        n_slices=len(sheet_measurements),
                        timestamp=time.time(),
                    )
                    yield result, sr
                    sheet_id += 1
                entry_encoder = None
                sheet_measurements = []

            yield result, None

            if step_delay_s > 0:
                time.sleep(step_delay_s)
