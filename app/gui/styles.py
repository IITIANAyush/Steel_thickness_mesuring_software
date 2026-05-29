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
}

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
    color: {PALETTE['text']};
    border: 1px solid {PALETTE['border_2']};
    border-radius: 5px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
    min-width: 76px;
}}

QPushButton:hover {{
    background-color: {PALETTE['accent_l']};
    border-color: {PALETTE['accent']};
    color: {PALETTE['accent']};
}}

QPushButton:pressed {{
    background-color: #D8E8F9;
}}

QPushButton:disabled {{
    color: #ABABAB;
    border-color: {PALETTE['border']};
    background-color: #F5F5F5;
}}

QPushButton#btnStart {{
    background-color: {PALETTE['accent']};
    color: #FFFFFF;
    border-color: {PALETTE['accent']};
    font-weight: 600;
}}
QPushButton#btnStart:hover {{
    background-color: {PALETTE['accent_h']};
    border-color: {PALETTE['accent_h']};
    color: #FFFFFF;
}}
QPushButton#btnStart:disabled {{
    background-color: #A0BAE0;
    border-color: #A0BAE0;
    color: #FFFFFF;
}}

QPushButton#btnStop {{
    background-color: {PALETTE['fail']};
    color: #FFFFFF;
    border-color: {PALETTE['fail']};
    font-weight: 600;
}}
QPushButton#btnStop:hover {{
    background-color: #B91C1C;
    border-color: #B91C1C;
    color: #FFFFFF;
}}
QPushButton#btnStop:disabled {{
    background-color: #F0AAAA;
    border-color: #F0AAAA;
    color: #FFFFFF;
}}

/* ═══════════════════════════════════════════════
   CARDS (QFrame)
═══════════════════════════════════════════════ */
QFrame#metricCard {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
}}

/* ═══════════════════════════════════════════════
   GROUP BOXES
═══════════════════════════════════════════════ */
QGroupBox {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    margin-top: 18px;
    padding: 10px 12px 10px 12px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 0px;
    padding: 0px 6px;
    background-color: {PALETTE['surface']};
    color: {PALETTE['muted']};
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}

/* ═══════════════════════════════════════════════
   LOG TABLE
═══════════════════════════════════════════════ */
QTableWidget {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    gridline-color: #F3F4F6;
    selection-background-color: {PALETTE['accent_l']};
    selection-color: {PALETTE['text']};
    outline: 0;
}}

QTableWidget::item {{
    padding: 5px 10px;
    font-size: 12px;
    font-family: "Consolas", "Courier New", monospace;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {PALETTE['accent_l']};
    color: {PALETTE['text']};
}}

QHeaderView {{
    background-color: transparent;
}}

QHeaderView::section {{
    background-color: #F8F9FB;
    color: {PALETTE['muted']};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid {PALETTE['border']};
    border-right: 1px solid #F0F2F5;
}}

QHeaderView::section:first {{
    border-top-left-radius: 7px;
}}

/* ═══════════════════════════════════════════════
   SCROLLBARS
═══════════════════════════════════════════════ */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #D1D5DB;
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: #9CA3AF;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: #D1D5DB;
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ═══════════════════════════════════════════════
   SPLITTER
═══════════════════════════════════════════════ */
QSplitter::handle {{
    background-color: {PALETTE['border']};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}

/* ═══════════════════════════════════════════════
   STATUS BAR
═══════════════════════════════════════════════ */
QStatusBar {{
    background-color: {PALETTE['surface']};
    border-top: 1px solid {PALETTE['border']};
    font-size: 11px;
    color: {PALETTE['muted']};
    padding: 2px 8px;
}}

/* ═══════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════ */
QProgressBar {{
    background-color: #EEF0F5;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    font-size: 10px;
}}
QProgressBar::chunk {{
    background-color: {PALETTE['accent']};
    border-radius: 4px;
}}

/* ═══════════════════════════════════════════════
   LABELS (named)
═══════════════════════════════════════════════ */
QLabel#cardLabel {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {PALETTE['muted']};
}}

QLabel#cardValue {{
    font-size: 36px;
    font-weight: 700;
    font-family: "Consolas", "Segoe UI", monospace;
    letter-spacing: -1px;
}}

QLabel#cardUnit {{
    font-size: 13px;
    color: {PALETTE['muted']};
    padding-bottom: 4px;
}}

QLabel#cardSub {{
    font-size: 11px;
    color: {PALETTE['muted']};
}}

QLabel#infoKey {{
    font-size: 11px;
    color: {PALETTE['muted']};
}}

QLabel#infoVal {{
    font-size: 12px;
    font-weight: 600;
    font-family: "Consolas", monospace;
    color: {PALETTE['text']};
}}

QLabel#sectionHeader {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {PALETTE['muted']};
    padding: 4px 0px 2px 0px;
}}
"""

# Alarm-specific styles (applied dynamically)
ALARM_OK   = f"color: {PALETTE['ok']}; background: {PALETTE['ok_bg']};"
ALARM_WARN = f"color: {PALETTE['warn']}; background: {PALETTE['warn_bg']};"
ALARM_FAIL = f"color: {PALETTE['fail']}; background: {PALETTE['fail_bg']};"
