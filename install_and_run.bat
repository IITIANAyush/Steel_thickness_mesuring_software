@echo off
REM ──────────────────────────────────────────────────────────
REM  Steel Thickness Monitor — Windows Setup & Run
REM  Double-click this file to install dependencies and launch.
REM ──────────────────────────────────────────────────────────

title Steel Thickness Monitor — Setup

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   Steel Thickness Monitor Setup      ║
echo  ║   Pando Data  /  Shear Sample System ║
echo  ╚══════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

echo  [1/3] Installing dependencies...
pip install PySide6 pyqtgraph numpy pandas scipy fastapi uvicorn --quiet
if errorlevel 1 (
    echo  [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)

echo  [2/3] Dependencies installed OK.
echo  [3/3] Launching application...
echo.

python run_app.py

pause
