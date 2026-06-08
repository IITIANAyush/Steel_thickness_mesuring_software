"""
SimulationEngine — Curved-profile sheet simulation with BendMode support.
The sheet cross-section (X-Z profile) is bent, not just vertically shifted,
so naive Z-difference gives wrong thickness and the parallel-tangent method
is needed.
"""

import time
from enum import Enum

import numpy as np
from scipy.interpolate import interp1d

from app.sensors.frame import Frame, ProfilePair, MeasurementResult, SheetResult
from app.sensors.simulation_loader import SimulationLoader
from app.processing.ThicknessCalculator import ThicknessCalculator
from app.processing.cosine_correction import cosine_correct
from app.processing.statistics import compute_statistics


SHEET_LENGTH_MM      = 400.0
PRE_BUFFER_MM        = 50.0
POST_BUFFER_MM       = 50.0
ENCODER_STEP_MM      = 2.0
TILT_ANGLE_RAD       = 0.003
SHEET_DETECT_Z_DELTA = 0.5
N_POINTS             = 512


class BendMode(Enum):
    FLAT    = "flat"
    BEND_X  = "bend_x"    # sinusoidal along conveyor (changes per-slice offset)
    BEND_Y  = "bend_y"    # parabolic crown across cross-section width
    BEND_XY = "bend_xy"   # both


class SimulationEngine:

    def __init__(
        self,
        top_csv:    str   = "data/top_profile.csv",
        bottom_csv: str   = "data/bottom_profile.csv",
        bend_mode:          str   = "bend_y",
        bend_amplitude_mm:  float = 3.0,
        bend_frequency:     float = 1.0,
        y_factor:           float = 1.0,
        add_noise:          bool  = True,
        noise_std_mm:       float = 0.02,
        add_crown:          bool  = False,
        crown_amplitude_mm: float = 0.5,
    ):
        loader = SimulationLoader()
        self.top_template    = loader.load_csv(top_csv,    sensor_id=0)
        self.bottom_template = loader.load_csv(bottom_csv, sensor_id=1)

        self._z_ref_top    = float(np.mean(self.top_template.z))
        self._z_ref_bottom = float(np.mean(self.bottom_template.z))
        self.d_calibration = self._z_ref_bottom - self._z_ref_top

        self.calc = ThicknessCalculator(d_calibration=self.d_calibration)

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

        _air_ref = (self._z_ref_top + self._z_ref_bottom) / 2.0
        self._z_top_air    = np.full(N_POINTS, _air_ref)
        self._z_bottom_air = np.full(N_POINTS, _air_ref)

        total_mm = PRE_BUFFER_MM + SHEET_LENGTH_MM + POST_BUFFER_MM
        self.encoder_positions = np.arange(0.0, total_mm, ENCODER_STEP_MM)
        self.sheet_entry = PRE_BUFFER_MM
        self.sheet_exit  = PRE_BUFFER_MM + SHEET_LENGTH_MM

        self._rng = np.random.default_rng(42)

        try:
            self._bend_mode = BendMode(bend_mode.lower())
        except ValueError:
            self._bend_mode = BendMode.BEND_Y

        self._bend_amplitude  = bend_amplitude_mm
        self._bend_frequency  = bend_frequency
        self._y_factor        = y_factor
        self._add_noise       = add_noise
        self._noise_std       = noise_std_mm
        self._add_crown       = add_crown
        self._crown_amplitude = crown_amplitude_mm
        self._y_common = np.zeros(N_POINTS)

        self.calibration_info = {
            "z_ref_top_mm":         round(self._z_ref_top,    3),
            "z_ref_bottom_mm":      round(self._z_ref_bottom, 3),
            "d_calibration_mm":     round(self.d_calibration, 3),
            "nominal_thickness_mm": round(self.d_calibration, 3),
        }

    def _crown_profile(self, x: np.ndarray, amplitude: float) -> np.ndarray:
        """Parabolic crown: max at centre, zero at edges."""
        x_norm = (x - x.mean()) / ((x.max() - x.min()) / 2.0 + 1e-9)
        return amplitude * (1.0 - x_norm ** 2)

    def _make_profile_pair_3d(self, encoder_pos: float, slice_idx: int) -> ProfilePair:
        sheet_here = self.sheet_entry <= encoder_pos < self.sheet_exit

        if not sheet_here:
            return ProfilePair(
                x_common=self.x_common,
                z_top=self._z_top_air.copy(),
                z_bottom=self._z_bottom_air.copy(),
                encoder_position=encoder_pos,
                timestamp=time.time(),
                slice_index=slice_idx,
                y_common=self._y_common.copy(),
                bend_disp=np.zeros(N_POINTS),
            )

        z_top    = self._z_top_sheet.copy()
        z_bottom = self._z_bottom_sheet.copy()

        rel = (encoder_pos - self.sheet_entry) / SHEET_LENGTH_MM

        # ── Cross-section curvature (bends the PROFILE shape, not just Z offset)
        # Top and bottom bend by the same crown → thickness stays correct
        # but Z-difference measurement will be wrong at the curved edges
        bend_profile = np.zeros(N_POINTS)

        if self._bend_mode in (BendMode.BEND_Y, BendMode.BEND_XY):
            # Parabolic crown across width — main realism source
            bend_profile += self._crown_profile(self.x_common, self._bend_amplitude * self._y_factor)

        if self._bend_mode in (BendMode.BEND_X, BendMode.BEND_XY):
            # Add a sinusoidal tilt that changes with encoder position
            # This makes the profile slope vary slice-to-slice
            tilt = self._bend_amplitude * 0.4 * np.sin(2 * np.pi * self._bend_frequency * rel)
            x_norm = (self.x_common - self.x_common.mean()) / ((self.x_common.max() - self.x_common.min()) / 2.0 + 1e-9)
            bend_profile += tilt * x_norm   # linear tilt across width

        # Apply bend to BOTH surfaces — thickness is preserved, but the
        # cross-section is now curved so Z-diff gives wrong result
        z_top    += bend_profile
        z_bottom += bend_profile

        if self._add_noise:
            z_top    += self._rng.normal(0, self._noise_std, N_POINTS)
            z_bottom += self._rng.normal(0, self._noise_std, N_POINTS)

        return ProfilePair(
            x_common=self.x_common,
            z_top=z_top,
            z_bottom=z_bottom,
            encoder_position=encoder_pos,
            timestamp=time.time(),
            slice_index=slice_idx,
            y_common=self._y_common.copy(),
            bend_disp=bend_profile,
        )

    def _detect_sheet(self, pair: ProfilePair) -> bool:
        mean_thickness = float(np.mean(pair.z_bottom - pair.z_top))
        return mean_thickness > SHEET_DETECT_Z_DELTA

    def _process_pair(self, pair: ProfilePair, sheet_present: bool) -> MeasurementResult:
        thickness_profile = self.calc.compute_profile(pair.z_top, pair.z_bottom)
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

    def run(self, step_delay_s: float = 0.05):
        """Flat backward-compatible generator. Yields (MeasurementResult, SheetResult|None)."""
        sheet_measurements = []
        entry_encoder = None
        sheet_id = 0

        for idx, enc in enumerate(self.encoder_positions):
            pair       = self._make_profile_pair_3d(enc, idx)
            sheet_here = self._detect_sheet(pair)
            result     = self._process_pair(pair, sheet_here)

            if sheet_here and entry_encoder is None:
                entry_encoder = enc
                sheet_measurements = []
            if sheet_here:
                sheet_measurements.append(result)

            if not sheet_here and entry_encoder is not None:
                if sheet_measurements:
                    all_means = [r.thickness_mean for r in sheet_measurements]
                    sr = SheetResult(
                        sheet_id=sheet_id,
                        entry_encoder=entry_encoder,
                        exit_encoder=enc,
                        length_mm=enc - entry_encoder,
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
                continue

            yield result, None
            if step_delay_s > 0:
                time.sleep(step_delay_s)

    def run_3d(self, step_delay_s: float = 0.05):
        """3D generator. Yields (ProfilePair, MeasurementResult, SheetResult|None)."""
        sheet_measurements = []
        entry_encoder = None
        sheet_id = 0

        for idx, enc in enumerate(self.encoder_positions):
            pair       = self._make_profile_pair_3d(enc, idx)
            sheet_here = self._detect_sheet(pair)
            result     = self._process_pair(pair, sheet_here)

            if sheet_here and entry_encoder is None:
                entry_encoder = enc
                sheet_measurements = []
            if sheet_here:
                sheet_measurements.append(result)

            sheet_out = None
            if not sheet_here and entry_encoder is not None:
                if sheet_measurements:
                    all_means = [r.thickness_mean for r in sheet_measurements]
                    sheet_out = SheetResult(
                        sheet_id=sheet_id,
                        entry_encoder=entry_encoder,
                        exit_encoder=enc,
                        length_mm=enc - entry_encoder,
                        thickness_mean=float(np.mean(all_means)),
                        thickness_min=float(np.min([r.thickness_min for r in sheet_measurements])),
                        thickness_max=float(np.max([r.thickness_max for r in sheet_measurements])),
                        thickness_std=float(np.std(all_means)),
                        n_slices=len(sheet_measurements),
                        timestamp=time.time(),
                    )
                    sheet_id += 1
                entry_encoder = None
                sheet_measurements = []

            yield pair, result, sheet_out
            if step_delay_s > 0:
                time.sleep(step_delay_s)
