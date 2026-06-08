"""
main_window.py — Steel Thickness Monitor (3D Parallel-Tangent Edition)
PySide6 + PyQtGraph GUI with:
  • Side-view plot: raw scan points, polynomial fit, tangent lines
  • Thickness-vs-encoder plot (live rolling)
  • Right panel: user-tunable parameters for simulator + calculator
  • Metric cards + measurement log
"""

import csv
import os
import sys
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore    import Qt, QThread, Slot, QSize
from PySide6.QtGui     import QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFrame, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter,
    QTabWidget, QTableWidget, QTableWidgetItem, QToolBar, QVBoxLayout,
    QWidget, QSpacerItem,
)

import pyqtgraph as pg
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.gui.styles  import STYLE_SHEET, ALARM_OK, ALARM_WARN, ALARM_FAIL, PALETTE
from app.gui.workers import Simulation3DWorker

NOMINAL_UM      = None   # auto from calibration
TOLERANCE_UM    = 200.0  # ±200 µm (adjustable)
CHART_POINTS    = 300
LOG_MAX_ROWS    = 500
TOTAL_ENC_MM    = 500.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _spin(lo, hi, val, dec=2, step=0.1, suffix=""):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setValue(val)
    s.setDecimals(dec)
    s.setSingleStep(step)
    if suffix:
        s.setSuffix(f" {suffix}")
    return s

def _ispin(lo, hi, val):
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(val)
    return s

def _row(label, widget):
    h = QHBoxLayout()
    h.setSpacing(6)
    lbl = QLabel(label)
    lbl.setObjectName("infoKey")
    lbl.setMinimumWidth(110)
    h.addWidget(lbl)
    h.addWidget(widget)
    return h


# ── Metric card ───────────────────────────────────────────────────────────────

class MetricCard(QFrame):
    def __init__(self, label, unit="µm", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(110)
        l = QVBoxLayout(self)
        l.setContentsMargins(14, 10, 14, 8)
        l.setSpacing(2)
        self._label = QLabel(label.upper())
        self._label.setObjectName("cardLabel")
        row = QHBoxLayout()
        row.setSpacing(4)
        self._value = QLabel("—")
        self._value.setObjectName("cardValue")
        self._value.setFont(QFont("Consolas", 26, QFont.Bold))
        self._unit = QLabel(unit)
        self._unit.setObjectName("cardUnit")
        self._unit.setAlignment(Qt.AlignBottom)
        row.addWidget(self._value); row.addWidget(self._unit); row.addStretch()
        self._sub = QLabel(""); self._sub.setObjectName("cardSub")
        self._badge = QLabel("")
        self._badge.setFixedHeight(20)
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.hide()
        l.addWidget(self._label); l.addLayout(row)
        l.addWidget(self._sub); l.addStretch()

    def update(self, value, sub="", status="neutral"):
        self._value.setText(f"{value:,.1f}")
        colors = {"ok": PALETTE["ok"], "warn": PALETTE["warn"],
                  "fail": PALETTE["fail"], "info": PALETTE["accent"],
                  "neutral": PALETTE["text"]}
        self._value.setStyleSheet(f"color: {colors.get(status, PALETTE['text'])};")
        self._sub.setText(sub)
        if status in ("ok", "warn", "fail"):
            labels = {"ok": "✓  OK", "warn": "⚠  WARN", "fail": "✗  FAIL"}
            styles = {"ok": ALARM_OK, "warn": ALARM_WARN, "fail": ALARM_FAIL}
            self._badge.setText(labels[status])
            self._badge.setStyleSheet(
                "font-size:10px;font-weight:700;letter-spacing:0.5px;"
                "border-radius:10px;padding:2px 10px;" + styles[status])
            self._badge.show()
        else:
            self._badge.hide()

    def reset(self):
        self._value.setText("—")
        self._value.setStyleSheet("")
        self._sub.setText("")
        self._badge.hide()


# ── Side-view plot (cross-section) ────────────────────────────────────────────

class SideViewPlot(pg.PlotWidget):
    """
    Shows the current cross-section scan:
      • Raw top/bottom scan points (scatter)
      • Polynomial fit curves
      • Tangent line segments at each measurement point
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent, background="#FAFAFA")
        self.setLabel("left",   "Z position (mm)", color="#6B7280", size="10pt")
        self.setLabel("bottom", "X position (mm)", color="#6B7280", size="10pt")
        self.setTitle("Cross-Section Side View", color="#374151", size="11pt")
        self.showGrid(x=True, y=True, alpha=0.25)
        self.getAxis("left").setTextPen(pg.mkPen("#6B7280"))
        self.getAxis("bottom").setTextPen(pg.mkPen("#6B7280"))

        # Raw scatter
        self._sc_top = pg.ScatterPlotItem(
            size=3, pen=None, brush=pg.mkBrush("#93C5FD"), name="Top raw")
        self._sc_bot = pg.ScatterPlotItem(
            size=3, pen=None, brush=pg.mkBrush("#FCA5A5"), name="Bottom raw")
        # Polynomial fit
        self._fit_top = self.plot([], [], pen=pg.mkPen("#1E6FD9", width=2), name="Top fit")
        self._fit_bot = self.plot([], [], pen=pg.mkPen("#DC2626", width=2), name="Bottom fit")
        # Tangent line items (pool of 30)
        self._tang_lines = []
        for _ in range(30):
            li = pg.PlotDataItem(pen=pg.mkPen("#059669", width=1.5, style=Qt.DashLine))
            self.addItem(li)
            self._tang_lines.append(li)

        self.addItem(self._sc_top)
        self.addItem(self._sc_bot)

        legend = self.addLegend(offset=(10, 10))
        legend.setLabelTextColor("#6B7280")
        self.setMouseEnabled(x=True, y=True)

    def update_profile(self, d: dict):
        x_top = d.get("x_top_raw", [])
        z_top = d.get("z_top_raw", [])
        x_bot = d.get("x_bot_raw", [])
        z_bot = d.get("z_bot_raw", [])
        x_fit = d.get("x_fit",    [])
        z_tf  = d.get("z_top_fit",[])
        z_bf  = d.get("z_bot_fit",[])
        tang_x  = d.get("tang_x",  [])
        tang_zt = d.get("tang_zt", [])
        tang_zb = d.get("tang_zb", [])
        tang_nx = d.get("tang_nx", [])
        tang_nz = d.get("tang_nz", [])
        tang_t  = d.get("tang_t",  [])

        if x_top:
            self._sc_top.setData(x_top, z_top)
            self._sc_bot.setData(x_bot, z_bot)
        if x_fit:
            self._fit_top.setData(x_fit, z_tf)
            self._fit_bot.setData(x_fit, z_bf)

        # Draw tangent segments (perpendicular through top surface)
        for i, li in enumerate(self._tang_lines):
            if i < len(tang_x) and tang_nx:
                xc   = tang_x[i]
                zt   = tang_zt[i]
                t_mm = tang_t[i] if i < len(tang_t) else 0.0
                nx   = tang_nx[i]
                nz   = tang_nz[i]
                # Draw the perpendicular segment from top to bottom surface
                seg_len = t_mm * 1.3
                x0 = xc - nx * 0.5 * seg_len
                z0 = zt - nz * 0.5 * seg_len
                x1 = xc + nx * seg_len
                z1 = zt + nz * seg_len
                li.setData([x0, x1], [z0, z1])
            else:
                li.setData([], [])

    def clear_data(self):
        self._sc_top.setData([], [])
        self._sc_bot.setData([], [])
        self._fit_top.setData([], [])
        self._fit_bot.setData([], [])
        for li in self._tang_lines:
            li.setData([], [])


# ── Thickness-vs-encoder chart ────────────────────────────────────────────────

class ThicknessChart(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent, background="w")
        self._enc  = deque(maxlen=CHART_POINTS)
        self._mean = deque(maxlen=CHART_POINTS)
        self._flags= deque(maxlen=CHART_POINTS)
        self._nominal_um = 10000.0  # updated from calibration

        self.setLabel("left",   "Thickness (µm)", color="#6B7280", size="10pt")
        self.setLabel("bottom", "Encoder position (mm)", color="#6B7280", size="10pt")
        self.showGrid(x=True, y=True, alpha=0.3)
        self.getAxis("left").setTextPen(pg.mkPen("#6B7280"))
        self.getAxis("bottom").setTextPen(pg.mkPen("#6B7280"))

        self._line_nom = pg.InfiniteLine(
            pos=self._nominal_um, angle=0,
            pen=pg.mkPen(PALETTE["ok"], width=1, style=Qt.DashLine))
        self._line_hi = pg.InfiniteLine(
            pos=self._nominal_um + TOLERANCE_UM, angle=0,
            pen=pg.mkPen(PALETTE["fail"], width=1, style=Qt.DashDotLine))
        self._line_lo = pg.InfiniteLine(
            pos=self._nominal_um - TOLERANCE_UM, angle=0,
            pen=pg.mkPen(PALETTE["fail"], width=1, style=Qt.DashDotLine))
        self.addItem(self._line_nom)
        self.addItem(self._line_hi)
        self.addItem(self._line_lo)

        self._curve_sheet = self.plot([], [], pen=pg.mkPen(PALETTE["accent"], width=2),
                                      name="Sheet")
        self._curve_air   = self.plot([], [], pen=None, symbol="o", symbolSize=3,
                                      symbolBrush=pg.mkBrush("#CBD0DB"), symbolPen=None,
                                      name="No sheet")
        self.addLegend(offset=(10, 10)).setLabelTextColor("#6B7280")
        self.setMouseEnabled(x=False, y=True)

    def set_nominal(self, nominal_um: float):
        self._nominal_um = nominal_um
        self._line_nom.setPos(nominal_um)
        self._line_hi.setPos(nominal_um + TOLERANCE_UM)
        self._line_lo.setPos(nominal_um - TOLERANCE_UM)

    def add_point(self, enc, thickness_um, sheet):
        self._enc.append(enc)
        self._mean.append(thickness_um)
        self._flags.append(sheet)
        enc_l = list(self._enc); mean_l = list(self._mean); fl = list(self._flags)
        sx, sy, ax, ay = [], [], [], []
        for e, m, f in zip(enc_l, mean_l, fl):
            if f: sx.append(e); sy.append(m)
            else: ax.append(e); ay.append(m)
        self._curve_sheet.setData(sx, sy)
        self._curve_air.setData(ax, ay)
        lo = max(0, thickness_um - 3000); hi = thickness_um + 3000
        self.setYRange(lo, hi, padding=0)

    def clear_data(self):
        self._enc.clear(); self._mean.clear(); self._flags.clear()
        self._curve_sheet.setData([], [])
        self._curve_air.setData([], [])


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steel Thickness Monitor — 3D Parallel-Tangent")
        self.setMinimumSize(1280, 760)
        self._worker   = None
        self._thread   = None
        self._history  = []
        self._slice_count = 0
        self._sheet_count = 0
        self._t_start  = None
        self._nominal_um = 10000.0

        pg.setConfigOptions(antialias=True)
        self._build_ui()
        self._reset_status()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self.setStyleSheet(STYLE_SHEET)

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.TopToolBarArea, tb)

        title_w = QWidget()
        tl = QVBoxLayout(title_w)
        tl.setContentsMargins(0, 0, 0, 0); tl.setSpacing(1)
        t1 = QLabel("Steel Thickness Monitor")
        t1.setObjectName("appTitle")
        t2 = QLabel("3D Parallel-Tangent Mode  |  Simulation")
        t2.setObjectName("appSubtitle")
        tl.addWidget(t1); tl.addWidget(t2)
        tb.addWidget(title_w)

        sp = QWidget(); sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(sp)

        self.btn_start = QPushButton("▶  Start")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self._start)

        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)

        self.btn_export = QPushButton("⬇  Export CSV")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_csv)

        for btn in (self.btn_start, self.btn_stop, self.btn_export):
            tb.addWidget(btn)

        self._lbl_live = QLabel("  ●  Ready")
        self._lbl_live.setStyleSheet(f"color:{PALETTE['muted']};font-weight:600;")
        tb.addWidget(self._lbl_live)

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        outer_split = QSplitter(Qt.Horizontal)
        root.addWidget(outer_split)

        # ── MAIN area (left+centre) ────────────────────────────────────
        main_w = QWidget()
        main_l = QVBoxLayout(main_w)
        main_l.setContentsMargins(14, 12, 8, 12)
        main_l.setSpacing(10)

        # Metric cards
        cr = QHBoxLayout(); cr.setSpacing(10)
        self.card_mean  = MetricCard("Thickness", "µm")
        self.card_min   = MetricCard("Minimum",   "µm")
        self.card_max   = MetricCard("Maximum",   "µm")
        self.card_sheet = MetricCard("Sheet",     "")
        for c in (self.card_mean, self.card_min, self.card_max, self.card_sheet):
            cr.addWidget(c)
        main_l.addLayout(cr)

        # Tab widget: side view | thickness chart
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.side_view   = SideViewPlot()
        self.thick_chart = ThicknessChart()

        self.tabs.addTab(self.side_view,   "Cross-Section View")
        self.tabs.addTab(self.thick_chart, "Thickness vs Encoder")
        main_l.addWidget(self.tabs, 1)

        # Log table
        lh = QLabel("MEASUREMENT LOG"); lh.setObjectName("sectionHeader")
        main_l.addWidget(lh)
        cols = ["Enc (mm)", "Mean (µm)", "Min (µm)", "Max (µm)", "Std (µm)", "Sheet", "Method"]
        self.log_table = QTableWidget(0, len(cols))
        self.log_table.setHorizontalHeaderLabels(cols)
        self.log_table.setFixedHeight(120)
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.verticalHeader().hide()
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setAlternatingRowColors(True)
        for i, w in enumerate([80, 90, 90, 90, 80, 55, 90]):
            self.log_table.setColumnWidth(i, w)
        main_l.addWidget(self.log_table)

        outer_split.addWidget(main_w)

        # ── RIGHT panel (parameters + info) ───────────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setMinimumWidth(240)
        right_scroll.setMaximumWidth(290)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 12, 14, 12)
        rl.setSpacing(10)

        # ── Simulation parameters ──────────────────────────────────────
        grp_sim = QGroupBox("Simulation")
        sl = QVBoxLayout(grp_sim)
        sl.setSpacing(6)

        self.sp_bend_mode = QComboBox()
        self.sp_bend_mode.addItems(["flat", "bend_y", "bend_x", "bend_xy"])
        self.sp_bend_mode.setCurrentText("bend_y")
        sl.addLayout(_row("Bend mode", self.sp_bend_mode))

        self.sp_bend_amp = _spin(0, 20, 3.0, dec=1, step=0.5, suffix="mm")
        sl.addLayout(_row("Bend amplitude", self.sp_bend_amp))

        self.sp_bend_freq = _spin(0.1, 5, 1.0, dec=1, step=0.1)
        sl.addLayout(_row("Bend frequency", self.sp_bend_freq))

        self.sp_y_factor = _spin(0, 3, 1.0, dec=1, step=0.1)
        sl.addLayout(_row("Y factor", self.sp_y_factor))

        self.chk_noise = QCheckBox("Add noise")
        self.chk_noise.setChecked(True)
        sl.addWidget(self.chk_noise)

        self.sp_noise = _spin(0, 1, 0.02, dec=3, step=0.005, suffix="mm")
        sl.addLayout(_row("Noise std", self.sp_noise))

        self.sp_delay = _spin(0, 0.5, 0.02, dec=3, step=0.005, suffix="s")
        sl.addLayout(_row("Step delay", self.sp_delay))

        rl.addWidget(grp_sim)

        # ── Measurement parameters ─────────────────────────────────────
        grp_meas = QGroupBox("Measurement")
        ml = QVBoxLayout(grp_meas)
        ml.setSpacing(6)

        self.sp_n_tang = _ispin(3, 50, 12)
        ml.addLayout(_row("# Tangents", self.sp_n_tang))

        self.sp_poly_deg = _ispin(1, 12, 6)
        ml.addLayout(_row("Poly degree", self.sp_poly_deg))

        self.sp_max_slope = _spin(1, 60, 15.0, dec=1, step=1.0, suffix="°")
        ml.addLayout(_row("Max slope", self.sp_max_slope))

        self.sp_smooth = _spin(0, 10, 1.0, dec=1, step=0.5)
        ml.addLayout(_row("Smoothing σ", self.sp_smooth))

        rl.addWidget(grp_meas)

        # ── Calibration info ───────────────────────────────────────────
        self.grp_calib = QGroupBox("Calibration")
        cl = QVBoxLayout(self.grp_calib)
        cl.setSpacing(5)
        self._calib_rows = {}
        for key, label in [
            ("d_calibration_mm",    "D cal"),
            ("z_ref_top_mm",        "Z top ref"),
            ("z_ref_bottom_mm",     "Z bot ref"),
            ("nominal_thickness_mm","Nominal"),
        ]:
            row = QHBoxLayout()
            k = QLabel(label); k.setObjectName("infoKey")
            v = QLabel("—");   v.setObjectName("infoVal"); v.setAlignment(Qt.AlignRight)
            row.addWidget(k); row.addWidget(v)
            cl.addLayout(row)
            self._calib_rows[key] = v
        rl.addWidget(self.grp_calib)

        # ── Encoder progress ───────────────────────────────────────────
        grp_enc = QGroupBox("Encoder")
        el = QVBoxLayout(grp_enc)
        el.setSpacing(5)
        self._lbl_enc = QLabel("0.0 mm")
        self._lbl_enc.setObjectName("cardValue")
        self._lbl_enc.setFont(QFont("Consolas", 18, QFont.Bold))
        self._enc_bar = QProgressBar()
        self._enc_bar.setRange(0, int(TOTAL_ENC_MM))
        self._enc_bar.setValue(0)
        self._enc_bar.setTextVisible(False)
        self._enc_bar.setFixedHeight(6)
        el.addWidget(self._lbl_enc); el.addWidget(self._enc_bar)
        rl.addWidget(grp_enc)

        # ── Session stats ──────────────────────────────────────────────
        grp_sess = QGroupBox("Session")
        sesl = QVBoxLayout(grp_sess); sesl.setSpacing(5)
        self._sess_rows = {}
        for key, lbl in [("slices","Slices"),("rate","Rate"),("sheets","Sheets")]:
            h = QHBoxLayout()
            k = QLabel(lbl); k.setObjectName("infoKey")
            v = QLabel("—"); v.setObjectName("infoVal"); v.setAlignment(Qt.AlignRight)
            h.addWidget(k); h.addWidget(v)
            sesl.addLayout(h)
            self._sess_rows[key] = v
        rl.addWidget(grp_sess)

        # ── Last sheet ─────────────────────────────────────────────────
        grp_sheet = QGroupBox("Last Sheet")
        shl = QVBoxLayout(grp_sheet); shl.setSpacing(5)
        self._sheet_rows = {}
        for key, lbl in [("id","Sheet #"),("length","Length"),
                          ("mean","Mean"),("range","Range"),("result","Result")]:
            h = QHBoxLayout()
            k = QLabel(lbl); k.setObjectName("infoKey")
            v = QLabel("—"); v.setObjectName("infoVal"); v.setAlignment(Qt.AlignRight)
            h.addWidget(k); h.addWidget(v)
            shl.addLayout(h)
            self._sheet_rows[key] = v
        rl.addWidget(grp_sheet)

        rl.addStretch()
        right_scroll.setWidget(right)
        outer_split.addWidget(right_scroll)
        outer_split.setSizes([1000, 270])
        outer_split.setHandleWidth(1)

    def _build_statusbar(self):
        sb = self.statusBar()
        self._status_msg = QLabel("Ready")
        sb.addWidget(self._status_msg)
        self._status_right = QLabel("")
        sb.addPermanentWidget(self._status_right)

    # ── Control ───────────────────────────────────────────────────────────

    def _start(self):
        if self._thread and self._thread.isRunning():
            return

        self._slice_count = 0; self._sheet_count = 0
        self._history.clear(); self._t_start = time.time()
        self.log_table.setRowCount(0)
        self.side_view.clear_data(); self.thick_chart.clear_data()
        for c in (self.card_mean, self.card_min, self.card_max, self.card_sheet):
            c.reset()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self._lbl_live.setText("  ●  Live")
        self._lbl_live.setStyleSheet(f"color:{PALETTE['ok']};font-weight:600;")
        self._status_msg.setText("Simulation running…")

        top_csv = str(ROOT / "data" / "top_profile.csv")
        bot_csv = str(ROOT / "data" / "bottom_profile.csv")

        self._worker = Simulation3DWorker(
            top_csv=top_csv, bottom_csv=bot_csv,
            step_delay=self.sp_delay.value(),
            # simulation
            bend_mode=self.sp_bend_mode.currentText(),
            bend_amplitude_mm=self.sp_bend_amp.value(),
            bend_frequency=self.sp_bend_freq.value(),
            y_factor=self.sp_y_factor.value(),
            add_noise=self.chk_noise.isChecked(),
            noise_std_mm=self.sp_noise.value(),
            # measurement
            n_tangents=self.sp_n_tang.value(),
            poly_degree=self.sp_poly_deg.value(),
            max_slope_deg=self.sp_max_slope.value(),
            smoothing_sigma=self.sp_smooth.value(),
        )

        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.calibReady.connect(self._on_calib)
        self._worker.sliceReady.connect(self._on_slice)
        self._worker.profileReady.connect(self._on_profile)
        self._worker.sheetReady.connect(self._on_sheet)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _stop(self):
        if self._worker:
            self._worker.stop()
        self._lbl_live.setText("  ●  Stopped")
        self._lbl_live.setStyleSheet(f"color:{PALETTE['warn']};font-weight:600;")
        self.btn_stop.setEnabled(False)

    # ── Slots ─────────────────────────────────────────────────────────────

    @Slot(dict)
    def _on_calib(self, info):
        for key, lbl in self._calib_rows.items():
            v = info.get(key)
            if v is not None:
                lbl.setText(f"{v:.3f} mm" if isinstance(v, float) else str(v))
        nominal_mm = info.get("nominal_thickness_mm")
        if nominal_mm:
            self._nominal_um = nominal_mm * 1000
            self.thick_chart.set_nominal(self._nominal_um)

    @Slot(dict)
    def _on_profile(self, d):
        """Update cross-section side view."""
        self.side_view.update_profile(d)

    @Slot(dict)
    def _on_slice(self, d):
        self._slice_count += 1
        self._history.append(d)

        enc  = d["encoder_mm"]
        mean = d["thickness_mean"]
        mn   = d["thickness_min"]
        mx   = d["thickness_max"]
        std  = d["thickness_std"]
        sp   = d["sheet_present"]
        meth = d.get("method", "flat")

        diff = abs(mean - self._nominal_um)
        if diff <= TOLERANCE_UM:          status = "ok"
        elif diff <= TOLERANCE_UM * 2:    status = "warn"
        else:                             status = "fail"

        if sp:
            self.card_mean.update(mean,  sub=f"{mean/1000:.3f} mm", status=status)
            self.card_min.update(mn,     sub=f"{mn/1000:.3f} mm")
            self.card_max.update(mx,     sub=f"{mx/1000:.3f} mm")
            self.card_sheet.update(0,    sub="Sheet detected", status="ok")
            self.card_sheet._value.setText("●")
            self.card_sheet._value.setStyleSheet(f"color:{PALETTE['ok']};")
        else:
            self.card_sheet.update(0, sub="No sheet", status="neutral")
            self.card_sheet._value.setText("○")
            self.card_sheet._value.setStyleSheet(f"color:{PALETTE['muted']};")

        self.thick_chart.add_point(enc, mean, sp)
        self._lbl_enc.setText(f"{enc:.1f} mm")
        self._enc_bar.setValue(int(enc))

        elapsed = time.time() - self._t_start if self._t_start else 0
        rate = self._slice_count / elapsed if elapsed > 0.5 else 0
        self._sess_rows["slices"].setText(str(self._slice_count))
        self._sess_rows["rate"].setText(f"{rate:.1f} /s")
        self._sess_rows["sheets"].setText(str(self._sheet_count))

        # Log table
        if self._slice_count > LOG_MAX_ROWS:
            self.log_table.removeRow(self.log_table.rowCount() - 1)
        self.log_table.insertRow(0)

        def cell(txt, color=None):
            item = QTableWidgetItem(txt)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if color:
                item.setForeground(QColor(color))
            return item

        col_color = (PALETTE["ok"] if status=="ok" else
                     PALETTE["warn"] if status=="warn" else PALETTE["fail"])
        self.log_table.setItem(0, 0, cell(f"{enc:.1f}"))
        self.log_table.setItem(0, 1, cell(f"{mean:.1f}", color=col_color if sp else None))
        self.log_table.setItem(0, 2, cell(f"{mn:.1f}"))
        self.log_table.setItem(0, 3, cell(f"{mx:.1f}"))
        self.log_table.setItem(0, 4, cell(f"{std:.1f}"))
        self.log_table.setItem(0, 5, cell("YES" if sp else "—",
                               color=PALETTE["ok"] if sp else PALETTE["muted"]))
        self.log_table.setItem(0, 6, cell(meth))
        self.log_table.setRowHeight(0, 22)

        self._status_right.setText(f"Enc: {enc:.1f} mm  |  Slices: {self._slice_count}")

    @Slot(dict)
    def _on_sheet(self, s):
        self._sheet_count += 1
        diff   = abs(s["mean_um"] - self._nominal_um)
        passed = diff <= TOLERANCE_UM
        self._sheet_rows["id"].setText(f"#{s['sheet_id']}")
        self._sheet_rows["length"].setText(f"{s['length_mm']:.1f} mm")
        self._sheet_rows["mean"].setText(f"{s['mean_um']:.1f} µm")
        self._sheet_rows["range"].setText(f"{s['min_um']:.0f} – {s['max_um']:.0f}")
        rl = self._sheet_rows["result"]
        if passed:
            rl.setText("✓  PASS"); rl.setStyleSheet(f"color:{PALETTE['ok']};font-weight:700;")
        else:
            rl.setText("✗  FAIL"); rl.setStyleSheet(f"color:{PALETTE['fail']};font-weight:700;")
        self._status_msg.setText(
            f"Sheet #{s['sheet_id']} — {s['length_mm']:.1f} mm, mean {s['mean_um']:.1f} µm")
        self.btn_export.setEnabled(True)

    @Slot()
    def _on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(bool(self._history))
        self._lbl_live.setText("  ●  Complete")
        self._lbl_live.setStyleSheet(f"color:{PALETTE['muted']};font-weight:600;")
        self._status_msg.setText(f"Complete — {self._slice_count} slices")

    def _export_csv(self):
        if not self._history:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "thickness_log.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self._history[0].keys())
            writer.writeheader(); writer.writerows(self._history)
        self._status_msg.setText(f"Exported {len(self._history)} rows → {path}")

    def _reset_status(self):
        self._lbl_live.setText("  ●  Ready")
        self._lbl_live.setStyleSheet(f"color:{PALETTE['muted']};font-weight:600;")

    def closeEvent(self, event):
        if self._worker: self._worker.stop()
        if self._thread: self._thread.quit(); self._thread.wait(2000)
        event.accept()
