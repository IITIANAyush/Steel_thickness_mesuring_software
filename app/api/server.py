"""
FastAPI Dashboard Server
========================
Runs the simulation engine in a background thread and streams live
measurements to the browser via Server-Sent Events (SSE).

Routes:
  GET /              → HTML dashboard (touchscreen friendly)
  GET /stream        → SSE stream of JSON measurements
  GET /api/calib     → calibration info
  GET /api/history   → last N measurements as JSON array
  GET /api/sheet     → last completed sheet summary
  GET /download/csv  → download measurement CSV
"""

import asyncio
import json
import os
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

# ── Add project root to path ─────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.sensors.simulation_engine import SimulationEngine
from app.export.csv_logger import CSVLogger


# ── Shared state (written by bg thread, read by SSE clients) ─────────────────
MAX_HISTORY = 300
_history: deque = deque(maxlen=MAX_HISTORY)
_last_sheet: Optional[dict] = None
_calib_info: Optional[dict] = None
_sse_queue: asyncio.Queue = None          # set after loop starts
_csv_logger: Optional[CSVLogger] = None

app = FastAPI(title="Steel Thickness Dashboard")


# ── Background simulation thread ─────────────────────────────────────────────

def _sim_thread(loop: asyncio.AbstractEventLoop):
    global _last_sheet, _calib_info, _csv_logger

    os.makedirs("logs", exist_ok=True)
    _csv_logger = CSVLogger("logs/thickness_log.csv")

    engine = SimulationEngine(
        top_csv="data/top_profile.csv",
        bottom_csv="data/bottom_profile.csv",
    )
    _calib_info = engine.calibration_info

    for result, sheet_result in engine.run(step_delay_s=0.06):
        point = {
            "encoder_mm":      round(result.encoder_position, 2),
            "thickness_mean":  round(result.thickness_mean * 1000, 1),   # → µm
            "thickness_min":   round(result.thickness_min  * 1000, 1),
            "thickness_max":   round(result.thickness_max  * 1000, 1),
            "thickness_std":   round(result.thickness_std  * 1000, 1),
            "sheet_present":   result.sheet_present,
            "timestamp":       round(result.timestamp, 3),
        }
        _history.append(point)

        # CSV logging (5 sample points across profile width)
        _n = len(engine.x_common)
        _idx = [0, _n//4, _n//2, 3*_n//4, _n-1]
        _csv_logger.log(
            timestamp=result.timestamp,
            encoder=result.encoder_position,
            x=engine.x_common[_idx],
            thickness=result.thickness_profile[_idx],
        )

        if sheet_result is not None:
            _last_sheet = {
                "sheet_id":        sheet_result.sheet_id,
                "length_mm":       round(sheet_result.length_mm, 1),
                "thickness_mean_um": round(sheet_result.thickness_mean * 1000, 1),
                "thickness_min_um":  round(sheet_result.thickness_min  * 1000, 1),
                "thickness_max_um":  round(sheet_result.thickness_max  * 1000, 1),
                "thickness_std_um":  round(sheet_result.thickness_std  * 1000, 1),
                "n_slices":        sheet_result.n_slices,
            }

        # Push to SSE queue (thread-safe)
        if _sse_queue is not None:
            payload = json.dumps(point)
            asyncio.run_coroutine_threadsafe(
                _sse_queue.put(payload), loop
            )


# ── FastAPI lifecycle ─────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global _sse_queue
    _sse_queue = asyncio.Queue(maxsize=2000)
    loop = asyncio.get_event_loop()
    t = threading.Thread(target=_sim_thread, args=(loop,), daemon=True)
    t.start()


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/calib")
def get_calib():
    return JSONResponse(_calib_info or {})


@app.get("/api/history")
def get_history():
    return JSONResponse(list(_history))


@app.get("/api/sheet")
def get_sheet():
    return JSONResponse(_last_sheet or {})


@app.get("/download/csv")
def download_csv():
    p = Path("logs/thickness_log.csv")
    if not p.exists():
        return JSONResponse({"error": "No log yet"}, status_code=404)
    return StreamingResponse(
        open(p, "rb"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=thickness_log.csv"},
    )


@app.get("/stream")
async def sse_stream():
    async def event_generator():
        yield "data: {\"type\":\"connected\"}\n\n"
        while True:
            try:
                payload = await asyncio.wait_for(_sse_queue.get(), timeout=2.0)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"   # keep-alive
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Dashboard HTML ────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Steel Thickness Monitor — Pando Data</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --accent: #f78166; --green: #3fb950; --yellow: #d29922;
    --red: #f85149; --blue: #58a6ff; --text: #e6edf3; --muted: #8b949e;
    --font: 'Segoe UI', system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--font);
         min-height: 100vh; overflow-x: hidden; }

  header {
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 14px 24px; display: flex; align-items: center; gap: 16px;
  }
  .logo { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
  .logo span { color: var(--accent); }
  .subtitle { font-size: 12px; color: var(--muted); }
  .status-dot { width: 10px; height: 10px; border-radius: 50%;
                background: var(--green); margin-left: auto;
                box-shadow: 0 0 8px var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

  .grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
          gap: 12px; padding: 20px 24px; }
  @media(max-width:900px) { .grid { grid-template-columns: 1fr 1fr; } }
  @media(max-width:500px) { .grid { grid-template-columns: 1fr; } }

  .card { background: var(--surface); border: 1px solid var(--border);
          border-radius: 10px; padding: 18px 20px; }
  .card-label { font-size: 11px; color: var(--muted); text-transform: uppercase;
                letter-spacing: 0.8px; margin-bottom: 8px; }
  .card-value { font-size: 38px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .card-unit  { font-size: 14px; color: var(--muted); margin-left: 4px; }
  .card-sub   { font-size: 12px; color: var(--muted); margin-top: 4px; }

  .val-green { color: var(--green); }
  .val-yellow{ color: var(--yellow); }
  .val-red   { color: var(--red); }
  .val-blue  { color: var(--blue); }

  .chart-wrap { grid-column: 1 / -1; }
  .chart-container { position: relative; height: 240px; }

  .sheet-card { grid-column: 1 / -1; background: var(--surface);
                border: 1px solid var(--border); border-radius: 10px;
                padding: 18px 20px; }
  .sheet-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr));
                gap: 16px; margin-top: 12px; }
  .sheet-metric { text-align: center; }
  .sheet-metric .label { font-size: 11px; color: var(--muted); text-transform: uppercase;
                          letter-spacing: 0.6px; }
  .sheet-metric .val   { font-size: 24px; font-weight: 600; margin-top: 4px; }

  .alarm { display: inline-block; padding: 3px 10px; border-radius: 20px;
           font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }
  .alarm-ok   { background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid var(--green); }
  .alarm-warn { background: rgba(210,153,34,0.15); color: var(--yellow); border: 1px solid var(--yellow); }
  .alarm-fail { background: rgba(248,81,73,0.15);  color: var(--red);    border: 1px solid var(--red); }

  .actions { padding: 0 24px 24px; display: flex; gap: 12px; flex-wrap: wrap; }
  .btn { padding: 10px 22px; border-radius: 8px; border: 1px solid var(--border);
         background: var(--surface); color: var(--text); font-size: 13px;
         cursor: pointer; transition: all .15s; text-decoration: none; }
  .btn:hover { border-color: var(--blue); color: var(--blue); }
  .btn-primary { background: var(--blue); border-color: var(--blue); color: #000;
                 font-weight: 600; }
  .btn-primary:hover { background: #79c0ff; color: #000; }

  .encoder-bar-wrap { height: 6px; background: var(--border); border-radius: 3px;
                      margin-top: 10px; overflow: hidden; }
  .encoder-bar { height: 100%; background: var(--blue); border-radius: 3px;
                 transition: width 0.1s linear; }
</style>
</head>
<body>

<header>
  <div>
    <div class="logo">Pando<span>Data</span> | Steel Thickness Monitor</div>
    <div class="subtitle">Shear Sample Measurement System — Simulation Mode</div>
  </div>
  <div class="status-dot" id="statusDot"></div>
</header>

<div class="grid">

  <!-- Thickness (mean) -->
  <div class="card">
    <div class="card-label">Thickness (mean)</div>
    <div>
      <span class="card-value val-green" id="thickMean">—</span>
      <span class="card-unit">µm</span>
    </div>
    <div class="card-sub" id="thickMeanMm">— mm</div>
    <div style="margin-top:8px" id="alarmBadge"><span class="alarm alarm-ok">OK</span></div>
  </div>

  <!-- Min / Max -->
  <div class="card">
    <div class="card-label">Min / Max this slice</div>
    <div>
      <span class="card-value val-blue" id="thickMin">—</span>
      <span class="card-unit">µm</span>
    </div>
    <div class="card-sub">Max: <span id="thickMax">—</span> µm</div>
    <div class="card-sub">Std: <span id="thickStd">—</span> µm</div>
  </div>

  <!-- Encoder position -->
  <div class="card">
    <div class="card-label">Encoder Position</div>
    <div>
      <span class="card-value val-blue" id="encPos">—</span>
      <span class="card-unit">mm</span>
    </div>
    <div class="card-sub" id="sheetStatus">Waiting...</div>
    <div class="encoder-bar-wrap">
      <div class="encoder-bar" id="encBar" style="width:0%"></div>
    </div>
  </div>

  <!-- Slices acquired -->
  <div class="card">
    <div class="card-label">Slices Acquired</div>
    <div>
      <span class="card-value val-yellow" id="sliceCount">0</span>
    </div>
    <div class="card-sub" id="sliceRate">—</div>
  </div>

  <!-- Live chart -->
  <div class="card chart-wrap">
    <div class="card-label">Live Thickness Profile (µm)</div>
    <div class="chart-container">
      <canvas id="thickChart"></canvas>
    </div>
  </div>

  <!-- Last sheet summary -->
  <div class="sheet-card">
    <div style="display:flex; align-items:center; gap:12px">
      <div class="card-label" style="margin:0">Last Sheet Result</div>
      <span class="alarm alarm-ok" id="sheetAlarm" style="display:none">—</span>
    </div>
    <div class="sheet-grid" id="sheetGrid">
      <div style="color:var(--muted); font-size:13px; grid-column:1/-1">
        Awaiting first sheet...</div>
    </div>
  </div>

</div>

<div class="actions">
  <a href="/download/csv" class="btn btn-primary">⬇ Download CSV</a>
  <a href="/api/history" class="btn" target="_blank">📊 History JSON</a>
  <a href="/api/sheet"   class="btn" target="_blank">📋 Sheet JSON</a>
  <a href="/api/calib"   class="btn" target="_blank">⚙ Calibration</a>
</div>

<script>
// ── Chart.js setup ────────────────────────────────────────────────────────
const MAX_PTS = 200;
const labels  = [];
const data    = { sheet: [], noSheet: [] };

const ctx = document.getElementById('thickChart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels,
    datasets: [
      {
        label: 'Sheet present (µm)',
        data: [],
        borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.08)',
        borderWidth: 2, pointRadius: 0, tension: 0.3, fill: true,
      },
      {
        label: 'No sheet (µm)',
        data: [],
        borderColor: '#8b949e', backgroundColor: 'transparent',
        borderWidth: 1, pointRadius: 0, tension: 0.3,
      },
    ],
  },
  options: {
    responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { legend: { labels: { color: '#8b949e', boxWidth: 12, font: {size:11} } } },
    scales: {
      x: { display: false },
      y: {
        grid: { color: 'rgba(48,54,61,0.8)' },
        ticks: { color: '#8b949e', font: { size: 11 } },
        title: { display: true, text: 'µm', color: '#8b949e' },
      },
    },
  },
});

// ── Helpers ───────────────────────────────────────────────────────────────
const NOMINAL_UM  = 10000;   // 10 mm nominal
const TOLERANCE   = 40;      // ±40 µm per brief

function setAlarm(meanUm) {
  const badge = document.getElementById('alarmBadge');
  const diff  = Math.abs(meanUm - NOMINAL_UM);
  let cls, txt;
  if (diff <= TOLERANCE)          { cls = 'alarm-ok';   txt = '✓ OK'; }
  else if (diff <= TOLERANCE * 2) { cls = 'alarm-warn'; txt = '⚠ WARN'; }
  else                            { cls = 'alarm-fail'; txt = '✗ FAIL'; }
  badge.innerHTML = `<span class="alarm ${cls}">${txt}</span>`;
}

function colorForThickness(um) {
  const diff = Math.abs(um - NOMINAL_UM);
  if (diff <= TOLERANCE)          return 'val-green';
  if (diff <= TOLERANCE * 2)      return 'val-yellow';
  return 'val-red';
}

let sliceCount = 0;
let lastTime   = Date.now();
let rateBuffer = [];

function updateRate() {
  const now = Date.now();
  rateBuffer.push(now - lastTime);
  if (rateBuffer.length > 10) rateBuffer.shift();
  lastTime = now;
  const avg = rateBuffer.reduce((a,b)=>a+b,0) / rateBuffer.length;
  document.getElementById('sliceRate').textContent =
    `~${(1000/avg).toFixed(1)} slices/s`;
}

// ── SSE listener ──────────────────────────────────────────────────────────
const es = new EventSource('/stream');

es.onmessage = (e) => {
  const d = JSON.parse(e.data);
  if (d.type === 'connected') return;

  sliceCount++;
  updateRate();

  const um = d.thickness_mean;
  document.getElementById('thickMean').textContent  = um.toLocaleString();
  document.getElementById('thickMean').className    = 'card-value ' + colorForThickness(um);
  document.getElementById('thickMeanMm').textContent= (um/1000).toFixed(3) + ' mm';
  document.getElementById('thickMin').textContent   = d.thickness_min.toLocaleString();
  document.getElementById('thickMax').textContent   = d.thickness_max.toLocaleString();
  document.getElementById('thickStd').textContent   = d.thickness_std.toLocaleString();
  document.getElementById('encPos').textContent     = d.encoder_mm.toFixed(1);
  document.getElementById('sliceCount').textContent = sliceCount;

  const pct = Math.min((d.encoder_mm / 500) * 100, 100);
  document.getElementById('encBar').style.width = pct + '%';

  const sheetEl = document.getElementById('sheetStatus');
  if (d.sheet_present) {
    sheetEl.innerHTML = '<span style="color:var(--green)">● Sheet detected</span>';
    setAlarm(um);
  } else {
    sheetEl.innerHTML = '<span style="color:var(--muted)">○ No sheet</span>';
  }

  // Rolling chart
  labels.push(d.encoder_mm.toFixed(0));
  if (labels.length > MAX_PTS) labels.shift();

  const ds0 = chart.data.datasets[0].data;
  const ds1 = chart.data.datasets[1].data;
  ds0.push(d.sheet_present ? um : null);
  ds1.push(d.sheet_present ? null : um);
  if (ds0.length > MAX_PTS) { ds0.shift(); ds1.shift(); }

  chart.update('none');

  // Fetch sheet summary after every 10th slice
  if (sliceCount % 10 === 0) fetchSheet();
};

es.onerror = () => {
  document.getElementById('statusDot').style.background = 'var(--red)';
};

// ── Sheet summary ─────────────────────────────────────────────────────────
function fetchSheet() {
  fetch('/api/sheet').then(r=>r.json()).then(s => {
    if (!s || !s.sheet_id === undefined) return;
    const grid = document.getElementById('sheetGrid');
    if (!s.sheet_id && s.sheet_id !== 0) return;
    const ok = Math.abs(s.thickness_mean_um - NOMINAL_UM) <= TOLERANCE;
    document.getElementById('sheetAlarm').style.display = '';
    document.getElementById('sheetAlarm').className = ok ? 'alarm alarm-ok' : 'alarm alarm-fail';
    document.getElementById('sheetAlarm').textContent = ok ? '✓ PASS' : '✗ FAIL';
    grid.innerHTML = [
      ['Sheet ID',    '#' + s.sheet_id],
      ['Length',      s.length_mm.toFixed(1) + ' mm'],
      ['Mean Thick',  s.thickness_mean_um.toFixed(1) + ' µm'],
      ['Min',         s.thickness_min_um.toFixed(1) + ' µm'],
      ['Max',         s.thickness_max_um.toFixed(1) + ' µm'],
      ['Std Dev',     s.thickness_std_um.toFixed(1) + ' µm'],
      ['Slices',      s.n_slices],
    ].map(([l,v]) => `
      <div class="sheet-metric">
        <div class="label">${l}</div>
        <div class="val">${v}</div>
      </div>`).join('');
  });
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


# ── Entry point ───────────────────────────────────────────────────────────────

def run(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run()
