# steel_monitor.spec
# ─────────────────────────────────────────────────────────────
# PyInstaller spec for Steel Thickness Monitor
#
# Build command (run from the steel_thickness_system folder):
#   pip install pyinstaller
#   pyinstaller steel_monitor.spec
#
# Output: dist/SteelThicknessMonitor.exe  (standalone, no installer needed)
# ─────────────────────────────────────────────────────────────

import sys
from pathlib import Path

ROOT = Path(".").resolve()

block_cipher = None

a = Analysis(
    ["run_app.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Bundled sensor data
        ("data/top_profile.csv",    "data"),
        ("data/bottom_profile.csv", "data"),
        ("config.json",             "."),
    ],
    hiddenimports=[
        "pyqtgraph",
        "pyqtgraph.graphicsItems",
        "scipy.signal",
        "scipy.interpolate",
        "scipy.special",
        "pandas",
        "numpy",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SteelThicknessMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # No console window (GUI app)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # Uncomment if you have an icon file
)
