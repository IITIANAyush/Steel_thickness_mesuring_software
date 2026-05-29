"""
workers.py — Background QThread worker for the simulation engine.
All heavy processing stays off the GUI thread; results are sent
via Qt signals so PySide6 can safely update the UI.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread

# Make sure the project root is importable
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.sensors.simulation_engine import SimulationEngine


class SimulationWorker(QObject):
    """
    Wraps SimulationEngine for use inside a QThread.

    Usage:
        worker = SimulationWorker(top_csv, bottom_csv)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.start()
    """

    # ── Signals ───────────────────────────────────────────────────────────
    # Emitted once when the engine has calibrated
    calibReady = Signal(dict)

    # Emitted for every encoder slice
    sliceReady = Signal(dict)      # {encoder_mm, thickness_mean, _min, _max, _std, sheet_present}

    # Emitted when a full sheet has passed through
    sheetReady = Signal(dict)      # {sheet_id, length_mm, mean_um, min_um, max_um, std_um, n_slices}

    # Emitted when the run loop exits (naturally or via stop())
    finished = Signal()

    def __init__(
        self,
        top_csv: str    = "data/top_profile.csv",
        bottom_csv: str = "data/bottom_profile.csv",
        step_delay: float = 0.05,   # seconds between slices
    ):
        super().__init__()
        self.top_csv    = top_csv
        self.bottom_csv = bottom_csv
        self.step_delay = step_delay
        self._running   = False

    # ── Slots ─────────────────────────────────────────────────────────────

    def run(self):
        """Main loop — called by QThread.started signal."""
        self._running = True
        try:
            engine = SimulationEngine(
                top_csv=self.top_csv,
                bottom_csv=self.bottom_csv,
            )
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
                })

                if sheet is not None:
                    self.sheetReady.emit({
                        "sheet_id":  sheet.sheet_id,
                        "length_mm": round(sheet.length_mm, 1),
                        "mean_um":   round(sheet.thickness_mean * 1000, 1),
                        "min_um":    round(sheet.thickness_min  * 1000, 1),
                        "max_um":    round(sheet.thickness_max  * 1000, 1),
                        "std_um":    round(sheet.thickness_std  * 1000, 1),
                        "n_slices":  sheet.n_slices,
                    })

        except Exception as exc:
            print(f"[SimulationWorker] Error: {exc}", flush=True)
        finally:
            self.finished.emit()

    def stop(self):
        """Request the run loop to exit cleanly."""
        self._running = False
