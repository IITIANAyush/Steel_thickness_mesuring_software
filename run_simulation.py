#!/usr/bin/env python3
"""
run_simulation.py
=================
Entry point for CSV-based simulation mode.

Usage:
  python run_simulation.py            # starts web dashboard on http://localhost:8000
  python run_simulation.py --cli      # console-only, no web server

Dashboard is accessible from any device on the same WiFi network:
  http://<mini-pc-ip>:8000
"""

import argparse
import sys
from pathlib import Path

# Allow running from the project root
sys.path.insert(0, str(Path(__file__).parent))


def run_cli():
    """Console mode: print measurements to stdout."""
    from app.sensors.simulation_engine import SimulationEngine
    import numpy as np

    engine = SimulationEngine(
        top_csv="data/top_profile.csv",
        bottom_csv="data/bottom_profile.csv",
    )

    print("\n── Calibration ──────────────────────────────────")
    for k, v in engine.calibration_info.items():
        print(f"  {k:<30}: {v}")
    print("─" * 50)
    print(f"{'Enc(mm)':>8}  {'Mean(µm)':>10}  {'Min':>8}  {'Max':>8}  {'Sheet':>6}")
    print("─" * 50)

    for result, sheet in engine.run(step_delay_s=0.0):
        flag = "YES" if result.sheet_present else "   "
        print(
            f"{result.encoder_position:8.1f}  "
            f"{result.thickness_mean*1000:10.1f}  "
            f"{result.thickness_min*1000:8.1f}  "
            f"{result.thickness_max*1000:8.1f}  "
            f"{flag}"
        )
        if sheet:
            print("\n" + "=" * 50)
            print(f"  SHEET #{sheet.sheet_id} COMPLETE")
            print(f"  Length   : {sheet.length_mm:.1f} mm")
            print(f"  Thickness: {sheet.thickness_mean*1000:.1f} µm mean  "
                  f"[{sheet.thickness_min*1000:.1f} – {sheet.thickness_max*1000:.1f}]")
            print("=" * 50 + "\n")


def run_server(host="0.0.0.0", port=8000):
    """Start web dashboard."""
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "localhost"

    print(f"\n  Steel Thickness Dashboard")
    print(f"  ─────────────────────────")
    print(f"  Local  : http://localhost:{port}")
    print(f"  Network: http://{local_ip}:{port}")
    print(f"\n  Press Ctrl+C to stop.\n")

    from app.api.server import run
    run(host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Steel Thickness Simulation")
    parser.add_argument("--cli",  action="store_true", help="Console-only mode")
    parser.add_argument("--host", default="0.0.0.0",   help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        run_server(host=args.host, port=args.port)
