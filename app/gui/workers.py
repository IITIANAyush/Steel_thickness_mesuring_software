"""
workers.py — Background QThread workers for the Steel Thickness Monitor.

SimulationWorker  : original flat-sheet worker (backward compatible)
Simulation3DWorker: new bend-aware worker using BendAwareThicknessCalculator
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.sensors.simulation_engine import SimulationEngine, BendMode
from app.processing.thickness_3d   import BendAwareThicknessCalculator


# ─────────────────────────────────────────────────────────────────────────────
# Original flat worker — kept for backward compatibility
# ─────────────────────────────────────────────────────────────────────────────

class SimulationWorker(QObject):
    calibReady = Signal(dict)
    sliceReady = Signal(dict)
    sheetReady = Signal(dict)
    finished   = Signal()

    def __init__(
        self,
        top_csv:    str   = "data/top_profile.csv",
        bottom_csv: str   = "data/bottom_profile.csv",
        step_delay: float = 0.05,
    ):
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
                    "thickness_mean": round(result.thickness_mean * 1000, 1),
                    "thickness_min":  round(result.thickness_min  * 1000, 1),
                    "thickness_max":  round(result.thickness_max  * 1000, 1),
                    "thickness_std":  round(result.thickness_std  * 1000, 1),
                    "sheet_present":  result.sheet_present,
                    "method":         "flat",
                    "bend_corrected": False,
                })
                if sheet is not None:
                    self._emit_sheet(sheet)
        except Exception as exc:
            print(f"[SimulationWorker] Error: {exc}", flush=True)
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


# ─────────────────────────────────────────────────────────────────────────────
# New 3-D bend-aware worker
# ─────────────────────────────────────────────────────────────────────────────

class Simulation3DWorker(QObject):
    """
    Runs SimulationEngine in 3-D mode and pipes every ProfilePair through
    BendAwareThicknessCalculator.  Exposes identical signals to
    SimulationWorker so the GUI can swap workers transparently.

    Extra signal:
        tangentReady(dict) — per-slice tangent-plane details for 3-D view
    """
    calibReady   = Signal(dict)
    sliceReady   = Signal(dict)
    sheetReady   = Signal(dict)
    tangentReady = Signal(dict)   # {encoder_mm, positions_x, thicknesses, normals_z}
    finished     = Signal()

    def __init__(
        self,
        top_csv:    str   = "data/top_profile.csv",
        bottom_csv: str   = "data/bottom_profile.csv",
        step_delay: float = 0.05,
        # ── simulation bend parameters ──────────────────────────────────
        bend_mode:         str   = "flat",
        bend_amplitude_mm: float = 0.0,
        bend_frequency:    float = 1.0,
        y_factor:          float = 0.0,
        add_noise:         bool  = False,
        noise_std_mm:      float = 0.030,
        add_crown:         bool  = False,
        crown_amplitude_mm:float = 0.5,
        # ── 3-D calculator parameters ───────────────────────────────────
        n_tangents:         int   = 10,
        tolerance_mm:       float = 0.5,
        nominal_mm:         float = 10.0,
        ransac_iterations:  int   = 50,
        smoothing_sigma:    float = 1.0,
        min_inliers_pct:    float = 0.3,
        neighbour_radius_mm:float = 15.0,
    ):
        super().__init__()
        self.top_csv    = top_csv
        self.bottom_csv = bottom_csv
        self.step_delay = step_delay
        self._running   = False

        # engine params
        self._eng_kwargs = dict(
            bend_mode          = bend_mode,
            bend_amplitude_mm  = bend_amplitude_mm,
            bend_frequency     = bend_frequency,
            y_factor           = y_factor,
            add_noise          = add_noise,
            noise_std_mm       = noise_std_mm,
            add_crown          = add_crown,
            crown_amplitude_mm = crown_amplitude_mm,
        )
        # calculator params
        self._calc_kwargs = dict(
            n_tangents          = n_tangents,
            tolerance_mm        = tolerance_mm,
            nominal_mm          = nominal_mm,
            ransac_iterations   = ransac_iterations,
            smoothing_sigma     = smoothing_sigma,
            min_inliers_pct     = min_inliers_pct,
            neighbour_radius_mm = neighbour_radius_mm,
        )

    def run(self):
        self._running = True
        try:
            engine = SimulationEngine(
                top_csv    = self.top_csv,
                bottom_csv = self.bottom_csv,
                **self._eng_kwargs,
            )
            calc = BendAwareThicknessCalculator(**self._calc_kwargs)

            self.calibReady.emit(dict(engine.calibration_info))

            sheet_measurements = []
            entry_encoder      = None
            sheet_id           = 0

            for pair, flat_result, sheet in engine.run_3d(step_delay_s=self.step_delay):
                if not self._running:
                    break

                # ── 3-D thickness calculation ────────────────────────────────
                if flat_result.sheet_present:
                    y = pair.y_common if pair.y_common is not None else \
                        __import__('numpy').zeros_like(pair.x_common)

                    res3d = calc.compute(
                        x_top = pair.x_common,
                        y_top = y,
                        z_top = pair.z_top,
                        x_bot = pair.x_common,
                        y_bot = y,
                        z_bot = pair.z_bottom,
                        encoder_position = pair.encoder_position,
                        timestamp        = pair.timestamp,
                        slice_index      = pair.slice_index,
                    )
                    mean_mm = res3d.thickness_mean
                    min_mm  = res3d.thickness_min
                    max_mm  = res3d.thickness_max
                    std_mm  = res3d.thickness_std
                    method  = "3d_tangent"
                    bend_ok = True

                    # Emit tangent-plane detail for 3-D visualisation panel
                    if res3d.measurements:
                        self.tangentReady.emit({
                            "encoder_mm":   round(pair.encoder_position, 2),
                            "positions_x":  [m.position_xyz[0] for m in res3d.measurements],
                            "thicknesses":  [round(m.thickness_mm * 1000, 1) for m in res3d.measurements],
                            "normals_z":    [round(float(m.normal_vector[2]), 4) for m in res3d.measurements],
                            "inliers":      [m.inlier_count for m in res3d.measurements],
                        })
                else:
                    # No sheet — use flat result (near zero)
                    mean_mm = flat_result.thickness_mean
                    min_mm  = flat_result.thickness_min
                    max_mm  = flat_result.thickness_max
                    std_mm  = flat_result.thickness_std
                    method  = "flat"
                    bend_ok = False

                self.sliceReady.emit({
                    "encoder_mm":     round(pair.encoder_position, 2),
                    "thickness_mean": round(mean_mm * 1000, 1),
                    "thickness_min":  round(min_mm  * 1000, 1),
                    "thickness_max":  round(max_mm  * 1000, 1),
                    "thickness_std":  round(std_mm  * 1000, 1),
                    "sheet_present":  flat_result.sheet_present,
                    "method":         method,
                    "bend_corrected": bend_ok,
                })

                # ── sheet accumulation for SheetResult ──────────────────────
                if flat_result.sheet_present and entry_encoder is None:
                    entry_encoder = pair.encoder_position
                    sheet_measurements = []

                if flat_result.sheet_present:
                    sheet_measurements.append({
                        "mean": mean_mm, "min": min_mm, "max": max_mm
                    })

                if sheet is not None:
                    if sheet_measurements:
                        import numpy as _np
                        means = [s["mean"] for s in sheet_measurements]
                        self.sheetReady.emit({
                            "sheet_id":  sheet_id,
                            "length_mm": round(sheet.length_mm, 1),
                            "mean_um":   round(float(_np.mean(means)) * 1000, 1),
                            "min_um":    round(float(_np.min([s["min"] for s in sheet_measurements])) * 1000, 1),
                            "max_um":    round(float(_np.max([s["max"] for s in sheet_measurements])) * 1000, 1),
                            "std_um":    round(float(_np.std(means)) * 1000, 1),
                            "n_slices":  len(sheet_measurements),
                        })
                        sheet_id += 1
                    entry_encoder = None
                    sheet_measurements = []

        except Exception as exc:
            print(f"[Simulation3DWorker] Error: {exc}", flush=True)
            import traceback; traceback.print_exc()
        finally:
            self.finished.emit()

    def stop(self):
        self._running = False
