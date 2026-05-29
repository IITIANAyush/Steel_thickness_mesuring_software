"""
main_window.py — Steel Thickness Monitor
PySide6 desktop application.
Clean modern Windows-style UI with live PyQtGraph chart.
"""

import csv
import os
import sys
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore    import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui     import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QStatusBar, QTableWidget, QTableWidgetItem,
    QToolBar, QVBoxLayout, QWidget, QSpacerItem,
)

import pyqtgraph as pg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.gui.styles  import STYLE_SHEET, ALARM_OK, ALARM_WARN, ALARM_FAIL, PALETTE
from app.gui.workers import SimulationWorker

# ── Constants ─────────────────────────────────────────────────────────────────
NOMINAL_UM   = 10_000.0   # 10 mm nominal thickness
TOLERANCE_UM = 40.0       # ±40 µm (per brief)
CHART_POINTS = 200        # rolling window
LOG_MAX_ROWS = 500
TOTAL_ENCODER_MM = 500.0  # simulated conveyor length


# ── Metric card widget ────────────────────────────────────────────────────────

class MetricCard(QFrame):
    """A KPI tile: label / large value / unit / sub-text / alarm badge."""

    def __init__(self, label: str, unit: str = "µm", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 10)
        layout.setSpacing(2)

        self._label = QLabel(label.upper())
        self._label.setObjectName("cardLabel")

        row = QHBoxLayout()
        row.setSpacing(4)
        self._value = QLabel("—")
        self._value.setObjectName("cardValue")
        self._value.setFont(QFont("Consolas", 28, QFont.Bold))
        self._unit  = QLabel(unit)
        self._unit.setObjectName("cardUnit")
        self._unit.setAlignment(Qt.AlignBottom)
        row.addWidget(self._value)
        row.addWidget(self._unit)
        row.addStretch()

        self._sub = QLabel("")
        self._sub.setObjectName("cardSub")

        self._badge = QLabel("")
        self._badge.setFixedHeight(20)
        self._badge.setAlignment(Qt.AlignCenter)
        badge_style = (
            "font-size: 10px; font-weight: 700; letter-spacing: 0.5px;"
            "border-radius: 10px; padding: 2px 10px;"
        )
        self._badge.setStyleSheet(badge_style)
        self._badge.hide()

        layout.addWidget(self._label)
        layout.addLayout(row)
        layout.addWidget(self._sub)
        layout.addStretch()

    def update(self, value: float, sub: str = "", status: str = "neutral"):
        """
        status: 'ok' | 'warn' | 'fail' | 'info' | 'neutral'
        """
        self._value.setText(f"{value:,.1f}")

        colors = {
            "ok":      PALETTE["ok"],
            "warn":    PALETTE["warn"],
            "fail":    PALETTE["fail"],
            "info":    PALETTE["accent"],
            "neutral": PALETTE["text"],
        }
        self._value.setStyleSheet(f"color: {colors.get(status, PALETTE['text'])};")
        self._sub.setText(sub)

        if status in ("ok", "warn", "fail"):
            labels = {"ok": "✓  OK", "warn": "⚠  WARN", "fail": "✗  FAIL"}
            styles = {"ok": ALARM_OK, "warn": ALARM_WARN, "fail": ALARM_FAIL}
            self._badge.setText(labels[status])
            self._badge.setStyleSheet(
                "font-size: 10px; font-weight: 700; letter-spacing: 0.5px;"
                "border-radius: 10px; padding: 2px 10px; " + styles[status]
            )
            self._badge.show()
        else:
            self._badge.hide()

    def reset(self):
        self._value.setText("—")
        self._value.setStyleSheet("")
        self._sub.setText("")
        self._badge.hide()


# ── Live chart ────────────────────────────────────────────────────────────────

class LiveChart(pg.PlotWidget):
    """Rolling thickness-vs-encoder PyQtGraph chart."""

    def __init__(self, parent=None):
        super().__init__(parent=parent, background="w")

        self._enc  = deque(maxlen=CHART_POINTS)
        self._mean = deque(maxlen=CHART_POINTS)

        # Styling
        self.setLabel("left",   "Thickness (µm)", color="#6B7280", size="11pt")
        self.setLabel("bottom", "Encoder (mm)",   color="#6B7280", size="11pt")
        self.showGrid(x=True, y=True, alpha=0.3)

        ax_style = {"color": "#6B7280", "font-size": "10pt"}
        self.getAxis("left").setTextPen(pg.mkPen(color="#6B7280"))
        self.getAxis("bottom").setTextPen(pg.mkPen(color="#6B7280"))
        self.getAxis("left").setPen(pg.mkPen(color="#E1E4EA", width=1))
        self.getAxis("bottom").setPen(pg.mkPen(color="#E1E4EA", width=1))

        # Alarm / nominal reference lines
        self._line_nom  = pg.InfiniteLine(
            pos=NOMINAL_UM, angle=0,
            pen=pg.mkPen(color=PALETTE["ok"], width=1, style=Qt.DashLine),
            label=f"Nominal {NOMINAL_UM/1000:.1f} mm",
            labelOpts={"color": PALETTE["ok"], "position": 0.98, "fill": None},
        )
        self._line_hi = pg.InfiniteLine(
            pos=NOMINAL_UM + TOLERANCE_UM, angle=0,
            pen=pg.mkPen(color=PALETTE["fail"], width=1, style=Qt.DashDotLine),
        )
        self._line_lo = pg.InfiniteLine(
            pos=NOMINAL_UM - TOLERANCE_UM, angle=0,
            pen=pg.mkPen(color=PALETTE["fail"], width=1, style=Qt.DashDotLine),
        )
        self.addItem(self._line_nom)
        self.addItem(self._line_hi)
        self.addItem(self._line_lo)

        # Sheet present: blue solid
        self._curve_sheet = self.plot(
            [], [],
            pen=pg.mkPen(color=PALETTE["accent"], width=2),
            name="Sheet present",
        )
        # No sheet: light gray dots
        self._curve_air = self.plot(
            [], [],
            pen=None,
            symbol="o", symbolSize=4,
            symbolBrush=pg.mkBrush("#CBD0DB"),
            symbolPen=None,
            name="No sheet",
        )

        # Legend
        legend = self.addLegend(offset=(10, 10))
        legend.setLabelTextColor("#6B7280")

        self.setMouseEnabled(x=False, y=True)

    def add_point(self, enc_mm: float, thickness_um: float, sheet: bool):
        self._enc.append(enc_mm)
        self._mean.append(thickness_um)

        enc_list  = list(self._enc)
        mean_list = list(self._mean)
        # Needs separate series for sheet / no-sheet
        # Use None gaps for each series
        sheet_y = [v if self._sheet_mask(i) else None for i, v in enumerate(mean_list)]
        air_y   = [v if not self._sheet_mask(i) else None for i, v in enumerate(mean_list)]

        # Track which indices are sheet/no-sheet
        if not hasattr(self, "_sheet_flags"):
            self._sheet_flags = deque(maxlen=CHART_POINTS)
        self._sheet_flags.append(sheet)

        flags = list(self._sheet_flags)
        # Rebuild sheet / air series with proper None gaps
        sx, sy, ax, ay = [], [], [], []
        for i, (e, m) in enumerate(zip(enc_list, mean_list)):
            if flags[i]:
                sx.append(e); sy.append(m)
            else:
                ax.append(e); ay.append(m)

        self._curve_sheet.setData(sx, sy)
        self._curve_air.setData(ax, ay)

        # Auto-range Y around current value
        lo = max(0, thickness_um - 2000)
        hi = thickness_um + 2000
        self.setYRange(lo, hi, padding=0)

    def _sheet_mask(self, i):
        if hasattr(self, "_sheet_flags"):
            flags = list(self._sheet_flags)
            if i < len(flags):
                return flags[i]
        return False

    def clear_data(self):
        self._enc.clear()
        self._mean.clear()
        if hasattr(self, "_sheet_flags"):
            self._sheet_flags.clear()
        self._curve_sheet.setData([], [])
        self._curve_air.setData([], [])


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steel Thickness Monitor — Pando Data")
        self.setMinimumSize(1100, 660)

        self._worker  = None
        self._thread  = None
        self._history = []          # full history for CSV export
        self._slice_count = 0
        self._t_start = None

        pg.setConfigOptions(antialias=True)

        self._build_ui()
        self._reset_status()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self):
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self.setStyleSheet(STYLE_SHEET)

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        tb.setIconSize(__import__("PySide6.QtCore", fromlist=["QSize"]).QSize(16, 16))
        self.addToolBar(Qt.TopToolBarArea, tb)

        # Title block
        title_block = QWidget()
        tbl = QVBoxLayout(title_block)
        tbl.setContentsMargins(0, 0, 0, 0)
        tbl.setSpacing(1)
        lbl_title = QLabel("Steel Thickness Monitor")
        lbl_title.setObjectName("appTitle")
        lbl_sub = QLabel("Shear Sample Measurement  |  Simulation Mode")
        lbl_sub.setObjectName("appSubtitle")
        tbl.addWidget(lbl_title)
        tbl.addWidget(lbl_sub)
        tb.addWidget(title_block)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        # Buttons
        self.btn_start = QPushButton("▶  Start")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self._start_simulation)

        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_simulation)

        self.btn_export = QPushButton("⬇  Export CSV")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_csv)

        for btn in (self.btn_start, self.btn_stop, self.btn_export):
            tb.addWidget(btn)
            tb.addSeparator() if btn is self.btn_stop else None

        # Live indicator
        self._lbl_live = QLabel("  ●  Ready")
        self._lbl_live.setStyleSheet(f"color: {PALETTE['muted']}; font-weight: 600;")
        tb.addWidget(self._lbl_live)

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        # ── LEFT ────────────────────────────────────────────────────────
        left = QWidget()
        left.setContentsMargins(0, 0, 0, 0)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 14, 10, 14)
        ll.setSpacing(12)

        # Metric cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        self.card_mean  = MetricCard("Thickness", "µm")
        self.card_min   = MetricCard("Minimum",   "µm")
        self.card_max   = MetricCard("Maximum",   "µm")
        self.card_sheet = MetricCard("Sheet",     "")

        for c in (self.card_mean, self.card_min, self.card_max, self.card_sheet):
            cards_row.addWidget(c)
        ll.addLayout(cards_row)

        # Live chart
        self.chart = LiveChart()
        self.chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ll.addWidget(self.chart, 1)

        # Log table header
        log_hdr = QLabel("MEASUREMENT LOG")
        log_hdr.setObjectName("sectionHeader")
        ll.addWidget(log_hdr)

        # Log table
        cols = ["Enc (mm)", "Mean (µm)", "Min (µm)", "Max (µm)", "Std (µm)", "Sheet"]
        self.log_table = QTableWidget(0, len(cols))
        self.log_table.setHorizontalHeaderLabels(cols)
        self.log_table.setFixedHeight(130)
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.verticalHeader().hide()
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #F8F9FB; }"
        )
        for i, w in enumerate([80, 90, 90, 90, 80, 60]):
            self.log_table.setColumnWidth(i, w)
        ll.addWidget(self.log_table)

        splitter.addWidget(left)

        # ── RIGHT (info panel) ────────────────────────────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setMinimumWidth(220)
        right_scroll.setMaximumWidth(270)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 14, 16, 14)
        rl.setSpacing(10)

        # Calibration group
        self.grp_calib = QGroupBox("Calibration")
        calib_layout = QVBoxLayout(self.grp_calib)
        calib_layout.setSpacing(6)
        self._calib_rows = {}
        for key, label in [
            ("d_calibration_mm",   "D calibration"),
            ("z_ref_top_mm",       "Z ref top"),
            ("z_ref_bottom_mm",    "Z ref bottom"),
            ("nominal_thickness_mm", "Nominal"),
        ]:
            row = QHBoxLayout()
            k = QLabel(label)
            k.setObjectName("infoKey")
            v = QLabel("—")
            v.setObjectName("infoVal")
            v.setAlignment(Qt.AlignRight)
            row.addWidget(k)
            row.addWidget(v)
            calib_layout.addLayout(row)
            self._calib_rows[key] = v
        rl.addWidget(self.grp_calib)

        # Encoder progress group
        self.grp_enc = QGroupBox("Encoder Position")
        enc_layout = QVBoxLayout(self.grp_enc)
        enc_layout.setSpacing(6)
        self._lbl_enc_pos = QLabel("0.0 mm")
        self._lbl_enc_pos.setObjectName("cardValue")
        self._lbl_enc_pos.setFont(QFont("Consolas", 20, QFont.Bold))
        self._enc_bar = QProgressBar()
        self._enc_bar.setRange(0, int(TOTAL_ENCODER_MM))
        self._enc_bar.setValue(0)
        self._enc_bar.setTextVisible(False)
        self._enc_bar.setFixedHeight(6)
        enc_layout.addWidget(self._lbl_enc_pos)
        enc_layout.addWidget(self._enc_bar)
        rl.addWidget(self.grp_enc)

        # Session stats group
        self.grp_session = QGroupBox("Session")
        sess_layout = QVBoxLayout(self.grp_session)
        sess_layout.setSpacing(6)
        self._sess_rows = {}
        for key, label in [
            ("slices", "Slices"),
            ("rate",   "Rate"),
            ("sheets", "Sheets"),
        ]:
            row = QHBoxLayout()
            k = QLabel(label)
            k.setObjectName("infoKey")
            v = QLabel("—")
            v.setObjectName("infoVal")
            v.setAlignment(Qt.AlignRight)
            row.addWidget(k)
            row.addWidget(v)
            sess_layout.addLayout(row)
            self._sess_rows[key] = v
        rl.addWidget(self.grp_session)

        # Last sheet group
        self.grp_sheet = QGroupBox("Last Sheet")
        sheet_layout = QVBoxLayout(self.grp_sheet)
        sheet_layout.setSpacing(6)
        self._sheet_rows = {}
        for key, label in [
            ("id",     "Sheet #"),
            ("length", "Length"),
            ("mean",   "Mean"),
            ("range",  "Range"),
            ("result", "Result"),
        ]:
            row = QHBoxLayout()
            k = QLabel(label)
            k.setObjectName("infoKey")
            v = QLabel("—")
            v.setObjectName("infoVal")
            v.setAlignment(Qt.AlignRight)
            row.addWidget(k)
            row.addWidget(v)
            sheet_layout.addLayout(row)
            self._sheet_rows[key] = v
        rl.addWidget(self.grp_sheet)

        rl.addStretch()
        right_scroll.setWidget(right)
        splitter.addWidget(right_scroll)

        splitter.setSizes([860, 240])
        splitter.setHandleWidth(1)

    def _build_statusbar(self):
        sb = self.statusBar()
        self._status_msg = QLabel("Ready")
        sb.addWidget(self._status_msg)
        self._status_right = QLabel("")
        sb.addPermanentWidget(self._status_right)

    # ── Simulation control ────────────────────────────────────────────────

    def _start_simulation(self):
        if self._thread and self._thread.isRunning():
            return

        # Reset UI
        self._slice_count = 0
        self._history.clear()
        self._sheet_count = 0
        self._t_start = time.time()
        self.log_table.setRowCount(0)
        self.chart.clear_data()
        for c in (self.card_mean, self.card_min, self.card_max, self.card_sheet):
            c.reset()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self._lbl_live.setText("  ●  Live")
        self._lbl_live.setStyleSheet(
            f"color: {PALETTE['ok']}; font-weight: 600;"
        )
        self._status_msg.setText("Simulation running…")

        # Worker + thread
        top_csv = str(ROOT / "data" / "top_profile.csv")
        bot_csv = str(ROOT / "data" / "bottom_profile.csv")

        self._worker = SimulationWorker(top_csv, bot_csv, step_delay=0.05)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.calibReady.connect(self._on_calib_ready)
        self._worker.sliceReady.connect(self._on_slice_ready)
        self._worker.sheetReady.connect(self._on_sheet_ready)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)

        self._thread.start()

    def _stop_simulation(self):
        if self._worker:
            self._worker.stop()
        self._lbl_live.setText("  ●  Stopped")
        self._lbl_live.setStyleSheet(
            f"color: {PALETTE['warn']}; font-weight: 600;"
        )
        self.btn_stop.setEnabled(False)

    # ── Slots ─────────────────────────────────────────────────────────────

    @Slot(dict)
    def _on_calib_ready(self, info: dict):
        for key, lbl in self._calib_rows.items():
            val = info.get(key)
            if val is not None:
                if isinstance(val, float):
                    lbl.setText(f"{val:.3f} mm")
                else:
                    lbl.setText(str(val))

    @Slot(dict)
    def _on_slice_ready(self, d: dict):
        self._slice_count += 1
        self._history.append(d)

        enc  = d["encoder_mm"]
        mean = d["thickness_mean"]
        mn   = d["thickness_min"]
        mx   = d["thickness_max"]
        std  = d["thickness_std"]
        sp   = d["sheet_present"]

        # Alarm status
        diff = abs(mean - NOMINAL_UM)
        if diff <= TOLERANCE_UM:
            status = "ok"
        elif diff <= TOLERANCE_UM * 2:
            status = "warn"
        else:
            status = "fail"

        # Update metric cards
        if sp:
            sub = f"{mean/1000:.3f} mm"
            self.card_mean.update(mean, sub=sub, status=status)
            self.card_min.update(mn,   sub=f"{mn/1000:.3f} mm")
            self.card_max.update(mx,   sub=f"{mx/1000:.3f} mm")
            self.card_sheet.update(0, sub="Sheet detected",  status="ok")
            self.card_sheet._value.setText("●")
            self.card_sheet._value.setStyleSheet(f"color: {PALETTE['ok']};")
        else:
            self.card_sheet.update(0, sub="No sheet", status="neutral")
            self.card_sheet._value.setText("○")
            self.card_sheet._value.setStyleSheet(f"color: {PALETTE['muted']};")

        # Chart
        self.chart.add_point(enc, mean, sp)

        # Encoder progress
        self._lbl_enc_pos.setText(f"{enc:.1f} mm")
        self._enc_bar.setValue(int(enc))

        # Session stats
        elapsed = time.time() - self._t_start if self._t_start else 0
        rate = self._slice_count / elapsed if elapsed > 0.5 else 0
        self._sess_rows["slices"].setText(str(self._slice_count))
        self._sess_rows["rate"].setText(f"{rate:.1f} /s")
        self._sess_rows["sheets"].setText(str(getattr(self, "_sheet_count", 0)))

        # Log table (insert at row 0 — newest on top)
        if self._slice_count <= LOG_MAX_ROWS:
            self.log_table.insertRow(0)
        else:
            self.log_table.removeRow(self.log_table.rowCount() - 1)
            self.log_table.insertRow(0)

        def cell(text, align=Qt.AlignRight, color=None):
            item = QTableWidgetItem(text)
            item.setTextAlignment(align | Qt.AlignVCenter)
            if color:
                item.setForeground(QColor(color))
            return item

        self.log_table.setItem(0, 0, cell(f"{enc:.1f}"))
        self.log_table.setItem(0, 1, cell(f"{mean:.1f}",
            color=PALETTE["ok"] if status == "ok" else
                  PALETTE["warn"] if status == "warn" else PALETTE["fail"]))
        self.log_table.setItem(0, 2, cell(f"{mn:.1f}"))
        self.log_table.setItem(0, 3, cell(f"{mx:.1f}"))
        self.log_table.setItem(0, 4, cell(f"{std:.1f}"))
        sheet_item = cell("YES" if sp else "—",
                          color=PALETTE["ok"] if sp else PALETTE["muted"])
        self.log_table.setItem(0, 5, sheet_item)

        self.log_table.setRowHeight(0, 24)

        # Status bar
        self._status_right.setText(
            f"Enc: {enc:.1f} mm  |  Slices: {self._slice_count}"
        )

    @Slot(dict)
    def _on_sheet_ready(self, s: dict):
        self._sheet_count = getattr(self, "_sheet_count", 0) + 1
        diff = abs(s["mean_um"] - NOMINAL_UM)
        passed = diff <= TOLERANCE_UM
        self._sheet_rows["id"].setText(f"#{s['sheet_id']}")
        self._sheet_rows["length"].setText(f"{s['length_mm']:.1f} mm")
        self._sheet_rows["mean"].setText(f"{s['mean_um']:.1f} µm")
        self._sheet_rows["range"].setText(
            f"{s['min_um']:.0f} – {s['max_um']:.0f}"
        )
        result_lbl = self._sheet_rows["result"]
        if passed:
            result_lbl.setText("✓  PASS")
            result_lbl.setStyleSheet(f"color: {PALETTE['ok']}; font-weight: 700;")
        else:
            result_lbl.setText("✗  FAIL")
            result_lbl.setStyleSheet(f"color: {PALETTE['fail']}; font-weight: 700;")

        self._status_msg.setText(
            f"Sheet #{s['sheet_id']} complete — "
            f"{s['length_mm']:.1f} mm length, "
            f"{s['mean_um']:.1f} µm mean"
        )
        self.btn_export.setEnabled(True)

    @Slot()
    def _on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(bool(self._history))
        self._lbl_live.setText("  ●  Complete")
        self._lbl_live.setStyleSheet(
            f"color: {PALETTE['muted']}; font-weight: 600;"
        )
        self._status_msg.setText(
            f"Simulation complete — {self._slice_count} slices acquired"
        )

    # ── Export CSV ────────────────────────────────────────────────────────

    def _export_csv(self):
        if not self._history:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Measurement CSV", "thickness_log.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self._history[0].keys())
            writer.writeheader()
            writer.writerows(self._history)
        self._status_msg.setText(f"Exported {len(self._history)} rows → {path}")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _reset_status(self):
        self._lbl_live.setText("  ●  Ready")
        self._lbl_live.setStyleSheet(
            f"color: {PALETTE['muted']}; font-weight: 600;"
        )
        self._sheet_count = 0

    def closeEvent(self, event):
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
        event.accept()
