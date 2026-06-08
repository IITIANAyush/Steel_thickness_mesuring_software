"""
workers.py — Background QThread workers for the Steel Thickness Monitor.
"""
from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.sensors.simulation_engine import SimulationEngine, BendMode
from app.processing.thickness_3d   import BendAwareThicknessCalculator


class SimulationWorker(QObject):
    """Flat worker — kept for backward compat."""
    calibReady = Signal(dict)
    sliceReady = Signal(dict)
    sheetReady = Signal(dict)
    finished   = Signal()

    def __init__(self, top_csv="data/top_profile.csv",
                 bottom_csv="data/bottom_profile.csv", step_delay=0.05):
        super().__init__()
        self.top_csv    = top_csv
        self.bottom_csv = bottom_csv
        self.step_delay = step_delay
        self._running   = False

    def run(self):
        self._running = True
        try:
            engine = SimulationEngine(top_csv=self.top_csv, bottom_csv=self.bottom_csv)
            self.calibReady.emit(dict(engine.calibration_info))
            for result, sheet in engine.run(step_delay_s=self.step_delay):
                if not self._running:
                    break
                self.sliceReady.emit({
                    "encoder_mm":     round(result.encoder_position, 2),
                    # thickness values are in mm — convert to µm for display
                    "thickness_mean": round(result.thickness_mean * 1000, 1),
                    "thickness_min":  round(result.thickness_min  * 1000, 1),
                    "thickness_max":  round(result.thickness_max  * 1000, 1),
                    "thickness_std":  round(result.thickness_std  * 1000, 1),
                    "sheet_present":  result.sheet_present,
                    "method":         "flat",
                    "bend_corrected": False,
                    # raw profile for side-view plot (subsample to 64 pts)
                    "x_profile":  result.thickness_profile[::8].tolist(),
                    "z_top":      [],
                    "z_bot":      [],
                })
                if sheet is not None:
                    self._emit_sheet(sheet)
        except Exception as exc:
            import traceback; traceback.print_exc()
        finally:
            self.finished.emit()

    def _emit_sheet(self, sheet):
        self.sheetReady.emit({
            "sheet_id":  sheet.sheet_id,
            "length_mm": round(sheet.length_mm, 1),
            "mean_um":   round(sheet.thickness_mean * 1000, 1),
            "min_um":    round(sheet.thickness_min  * 1000, 1),
            "max_um":    round(sheet.thickness_max  * 1000, 1),
            "std_um":    round(sheet.thickness_std  * 1000, 1),
            "n_slices":  sheet.n_slices,
        })

    def stop(self):
        self._running = False


class Simulation3DWorker(QObject):
    """
    3-D bend-aware worker.  Uses BendAwareThicknessCalculator (parallel-tangent).

    Signals
    -------
    sliceReady(dict)   — per-slice thickness + profile data for all plots
    profileReady(dict) — full scan geometry for side-view + tangent overlay
    sheetReady(dict)   — end-of-sheet summary
    calibReady(dict)   — calibration info
    """
    calibReady   = Signal(dict)
    sliceReady   = Signal(dict)
    sheetReady   = Signal(dict)
    profileReady = Signal(dict)   # side-view + tangent data
    finished     = Signal()

    def __init__(
        self,
        top_csv="data/top_profile.csv",
        bottom_csv="data/bottom_profile.csv",
        step_delay=0.02,
        # simulation
        bend_mode="bend_y",
        bend_amplitude_mm=3.0,
        bend_frequency=1.0,
        y_factor=1.0,
        add_noise=True,
        noise_std_mm=0.02,
        # calculator
        n_tangents=12,
        poly_degree=6,
        max_slope_deg=15.0,
        smoothing_sigma=1.0,
        nominal_mm=None,   # auto from calibration
    ):
        super().__init__()
        self.top_csv    = top_csv
        self.bottom_csv = bottom_csv
        self.step_delay = step_delay
        self._running   = False

        self._eng_kw = dict(
            bend_mode=bend_mode,
            bend_amplitude_mm=bend_amplitude_mm,
            bend_frequency=bend_frequency,
            y_factor=y_factor,
            add_noise=add_noise,
            noise_std_mm=noise_std_mm,
        )
        self._calc_kw = dict(
            n_tangents=n_tangents,
            poly_degree=poly_degree,
            max_slope_deg=max_slope_deg,
            smoothing_sigma=smoothing_sigma,
            nominal_mm=nominal_mm,  # filled after calibration
        )

    def run(self):
        self._running = True
        try:
            engine = SimulationEngine(
                top_csv=self.top_csv, bottom_csv=self.bottom_csv, **self._eng_kw
            )
            self.calibReady.emit(dict(engine.calibration_info))

            # Auto nominal from calibration if not set
            nominal = self._calc_kw.get("nominal_mm") or engine.d_calibration
            calc_kw = {**self._calc_kw, "nominal_mm": nominal}
            calc = BendAwareThicknessCalculator(**calc_kw)

            sheet_measurements = []
            entry_encoder      = None
            sheet_id           = 0

            for pair, flat_result, sheet_trigger in engine.run_3d(step_delay_s=self.step_delay):
                if not self._running:
                    break

                if flat_result.sheet_present:
                    res3d = calc.compute(
                        x_top=pair.x_common, z_top=pair.z_top,
                        x_bot=pair.x_common, z_bot=pair.z_bottom,
                        encoder_position=pair.encoder_position,
                        timestamp=pair.timestamp,
                        slice_index=pair.slice_index,
                    )
                    mean_mm = res3d.thickness_mean
                    min_mm  = res3d.thickness_min
                    max_mm  = res3d.thickness_max
                    std_mm  = res3d.thickness_std

                    # Emit full profile geometry for plots
                    tang_x  = [m.x_pos       for m in res3d.measurements]
                    tang_zt = [m.z_top        for m in res3d.measurements]
                    tang_zb = [m.z_bot        for m in res3d.measurements]
                    tang_t  = [m.thickness_mm for m in res3d.measurements]
                    tang_nx = [m.normal[0]    for m in res3d.measurements]
                    tang_nz = [m.normal[1]    for m in res3d.measurements]

                    self.profileReady.emit({
                        "encoder_mm":  round(pair.encoder_position, 2),
                        # raw scan data (subsample for speed)
                        "x_top_raw":   pair.x_common[::4].tolist(),
                        "z_top_raw":   pair.z_top[::4].tolist(),
                        "x_bot_raw":   pair.x_common[::4].tolist(),
                        "z_bot_raw":   pair.z_bottom[::4].tolist(),
                        # polynomial fit
                        "x_fit":       res3d.x_fit[::4].tolist(),
                        "z_top_fit":   res3d.z_top_fit[::4].tolist(),
                        "z_bot_fit":   res3d.z_bot_fit[::4].tolist(),
                        # tangent measurements
                        "tang_x":  tang_x,
                        "tang_zt": tang_zt,
                        "tang_zb": tang_zb,
                        "tang_t":  tang_t,
                        "tang_nx": tang_nx,
                        "tang_nz": tang_nz,
                    })
                else:
                    mean_mm = flat_result.thickness_mean
                    min_mm  = flat_result.thickness_min
                    max_mm  = flat_result.thickness_max
                    std_mm  = flat_result.thickness_std

                self.sliceReady.emit({
                    "encoder_mm":     round(pair.encoder_position, 2),
                    "thickness_mean": round(mean_mm * 1000, 1),   # → µm
                    "thickness_min":  round(min_mm  * 1000, 1),
                    "thickness_max":  round(max_mm  * 1000, 1),
                    "thickness_std":  round(std_mm  * 1000, 1),
                    "sheet_present":  flat_result.sheet_present,
                    "method":         "3d_tangent" if flat_result.sheet_present else "flat",
                    "bend_corrected": flat_result.sheet_present,
                })

                if flat_result.sheet_present and entry_encoder is None:
                    entry_encoder = pair.encoder_position
                    sheet_measurements = []
                if flat_result.sheet_present:
                    sheet_measurements.append(mean_mm)

                if sheet_trigger is not None:
                    if sheet_measurements:
                        import numpy as _np
                        self.sheetReady.emit({
                            "sheet_id":  sheet_id,
                            "length_mm": round(sheet_trigger.length_mm, 1),
                            "mean_um":   round(float(_np.mean(sheet_measurements)) * 1000, 1),
                            "min_um":    round(float(_np.min(sheet_measurements))  * 1000, 1),
                            "max_um":    round(float(_np.max(sheet_measurements))  * 1000, 1),
                            "std_um":    round(float(_np.std(sheet_measurements))  * 1000, 1),
                            "n_slices":  len(sheet_measurements),
                        })
                        sheet_id += 1
                    entry_encoder      = None
                    sheet_measurements = []

        except Exception:
            import traceback; traceback.print_exc()
        finally:
            self.finished.emit()

    def stop(self):
        self._running = False
