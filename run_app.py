#!/usr/bin/env python3
"""
run_app.py — Steel Thickness Monitor (Windows Desktop App)
==========================================================
Launches the PySide6 GUI.

Usage:
    python run_app.py

Requirements:
    pip install PySide6 pyqtgraph numpy pandas scipy
"""

import sys
import os
from pathlib import Path

# Ensure project root is on the path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    # High-DPI support for Windows
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore    import Qt
        from PySide6.QtGui     import QFont
    except ImportError:
        print("PySide6 is not installed. Run:  pip install PySide6")
        sys.exit(1)

    try:
        import pyqtgraph  # noqa: F401
    except ImportError:
        print("PyQtGraph is not installed. Run:  pip install pyqtgraph")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("Steel Thickness Monitor")
    app.setOrganizationName("Pando Data")
    app.setApplicationVersion("1.0.0")

    # Use the default Windows system font (Segoe UI)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    from app.gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
