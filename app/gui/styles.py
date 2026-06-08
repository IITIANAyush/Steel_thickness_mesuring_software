"""
styles.py — Windows Fluent-inspired QSS stylesheet
Precision instrument aesthetic: clinical white, electric blue, tabular numbers.
"""

PALETTE = {
    "bg":        "#F5F6FA",
    "surface":   "#FFFFFF",
    "border":    "#E1E4EA",
    "border_2":  "#CBD0DB",
    "accent":    "#1E6FD9",
    "accent_h":  "#1558B0",
    "accent_l":  "#EBF2FD",
    "text":      "#111827",
    "muted":     "#6B7280",
    "ok":        "#059669",
    "ok_bg":     "#ECFDF5",
    "warn":      "#D97706",
    "warn_bg":   "#FFFBEB",
    "fail":      "#DC2626",
    "fail_bg":   "#FEF2F2",
    "info":      "#7C3AED",
    "info_bg":   "#F5F3FF",
}

ALARM_OK   = f"background-color: {PALETTE['ok_bg']};   color: {PALETTE['ok']};"
ALARM_WARN = f"background-color: {PALETTE['warn_bg']}; color: {PALETTE['warn']};"
ALARM_FAIL = f"background-color: {PALETTE['fail_bg']}; color: {PALETTE['fail']};"
ALARM_INFO = f"background-color: {PALETTE['info_bg']}; color: {PALETTE['info']};"

STYLE_SHEET = f"""
/* ═══════════════════════════════════════════════
   BASE
═══════════════════════════════════════════════ */
QMainWindow {{
    background-color: {PALETTE['bg']};
}}

QWidget {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {PALETTE['text']};
    background-color: transparent;
}}

/* ═══════════════════════════════════════════════
   TOOLBAR
═══════════════════════════════════════════════ */
QToolBar {{
    background-color: {PALETTE['surface']};
    border: none;
    border-bottom: 1px solid {PALETTE['border']};
    spacing: 4px;
    padding: 6px 16px;
}}

QToolBar QLabel#appTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {PALETTE['accent']};
    letter-spacing: -0.3px;
}}

QToolBar QLabel#appSubtitle {{
    font-size: 11px;
    color: {PALETTE['muted']};
}}

/* ═══════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════ */
QPushButton {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border_2']};
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
    color: {PALETTE['text']};
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {PALETTE['accent_l']};
    border-color: {PALETTE['accent']};
    color: {PALETTE['accent']};
}}

QPushButton:pressed {{
    background-color: {PALETTE['accent']};
    color: #ffffff;
}}

QPushButton:disabled {{
    color: {PALETTE['muted']};
    border-color: {PALETTE['border']};
    background-color: {PALETTE['bg']};
}}

QPushButton#btnStart {{
    background-color: {PALETTE['accent']};
    color: #ffffff;
    border: none;
}}

QPushButton#btnStart:hover {{
    background-color: {PALETTE['accent_h']};
    color: #ffffff;
}}

QPushButton#btnStart:disabled {{
    background-color: {PALETTE['border_2']};
    color: {PALETTE['muted']};
}}

QPushButton#btnStop {{
    color: {PALETTE['fail']};
    border-color: {PALETTE['fail']};
}}

QPushButton#btnStop:hover {{
    background-color: {PALETTE['fail_bg']};
}}

/* ═══════════════════════════════════════════════
   METRIC CARDS
═══════════════════════════════════════════════ */
QFrame#metricCard {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
}}

QLabel#cardLabel {{
    font-size: 10px;
    font-weight: 700;
    color: {PALETTE['muted']};
    letter-spacing: 0.8px;
}}

QLabel#cardUnit {{
    font-size: 12px;
    color: {PALETTE['muted']};
    margin-bottom: 4px;
}}

QLabel#cardSub {{
    font-size: 11px;
    color: {PALETTE['muted']};
}}

/* ═══════════════════════════════════════════════
   GROUP BOXES
═══════════════════════════════════════════════ */
QGroupBox {{
    font-weight: 700;
    font-size: 11px;
    color: {PALETTE['muted']};
    letter-spacing: 0.5px;
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    background-color: {PALETTE['surface']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: -1px;
    background-color: {PALETTE['surface']};
    padding: 0 4px;
}}

/* ═══════════════════════════════════════════════
   SPIN BOXES, COMBO BOXES, LINE EDITS
═══════════════════════════════════════════════ */
QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border_2']};
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 26px;
    color: {PALETTE['text']};
}}

QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{
    border-color: {PALETTE['accent']};
}}

QDoubleSpinBox::up-button, QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid {PALETTE['border']};
    border-bottom: 1px solid {PALETTE['border']};
    border-top-right-radius: 5px;
}}

QDoubleSpinBox::down-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid {PALETTE['border']};
    border-bottom-right-radius: 5px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border_2']};
    selection-background-color: {PALETTE['accent_l']};
    selection-color: {PALETTE['accent']};
}}

/* ═══════════════════════════════════════════════
   CHECKBOXES
═══════════════════════════════════════════════ */
QCheckBox {{
    spacing: 6px;
    color: {PALETTE['text']};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {PALETTE['border_2']};
    border-radius: 4px;
    background-color: {PALETTE['surface']};
}}

QCheckBox::indicator:checked {{
    background-color: {PALETTE['accent']};
    border-color: {PALETTE['accent']};
}}

/* ═══════════════════════════════════════════════
   LABELS — info panel
═══════════════════════════════════════════════ */
QLabel#infoKey {{
    font-size: 11px;
    color: {PALETTE['muted']};
}}

QLabel#infoVal {{
    font-size: 11px;
    font-weight: 600;
    color: {PALETTE['text']};
    font-family: "Consolas", monospace;
}}

QLabel#sectionHeader {{
    font-size: 10px;
    font-weight: 700;
    color: {PALETTE['muted']};
    letter-spacing: 0.8px;
    padding: 4px 0 2px 0;
}}

/* ═══════════════════════════════════════════════
   TABLE
═══════════════════════════════════════════════ */
QTableWidget {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
    gridline-color: {PALETTE['border']};
    font-size: 11px;
    font-family: "Consolas", monospace;
}}

QTableWidget::item {{
    padding: 2px 6px;
}}

QHeaderView::section {{
    background-color: {PALETTE['bg']};
    border: none;
    border-bottom: 1px solid {PALETTE['border']};
    border-right: 1px solid {PALETTE['border']};
    font-size: 10px;
    font-weight: 700;
    color: {PALETTE['muted']};
    letter-spacing: 0.5px;
    padding: 4px 6px;
}}

/* ═══════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════ */
QProgressBar {{
    border: none;
    border-radius: 3px;
    background-color: {PALETTE['bg']};
}}

QProgressBar::chunk {{
    background-color: {PALETTE['accent']};
    border-radius: 3px;
}}

/* ═══════════════════════════════════════════════
   SCROLL AREA / SCROLL BAR
═══════════════════════════════════════════════ */
QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {PALETTE['border_2']};
    border-radius: 3px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ═══════════════════════════════════════════════
   SPLITTER
═══════════════════════════════════════════════ */
QSplitter::handle {{
    background-color: {PALETTE['border']};
}}

/* ═══════════════════════════════════════════════
   STATUS BAR
═══════════════════════════════════════════════ */
QStatusBar {{
    background-color: {PALETTE['surface']};
    border-top: 1px solid {PALETTE['border']};
    font-size: 11px;
    color: {PALETTE['muted']};
}}

/* ═══════════════════════════════════════════════
   TOOLTIPS
═══════════════════════════════════════════════ */
QToolTip {{
    background-color: {PALETTE['text']};
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ═══════════════════════════════════════════════
   BADGE LABELS (method / bend indicator)
═══════════════════════════════════════════════ */
QLabel#badge3d {{
    background-color: {PALETTE['info_bg']};
    color: {PALETTE['info']};
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 10px;
    font-weight: 700;
}}

QLabel#badgeFlat {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['muted']};
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 10px;
    font-weight: 700;
    border: 1px solid {PALETTE['border']};
}}
"""
