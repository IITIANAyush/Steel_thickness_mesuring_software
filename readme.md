# Steel Thickness Monitoring System

Industrial-style real-time steel thickness monitoring and analysis software built in Python.

This system simulates or processes laser sensor data, computes strip thickness, applies filtering and calibration, visualizes measurements in real time, and exports results for industrial quality-control workflows.

---

# Features

## Core Features

* Real-time sensor acquisition
* CSV-based simulation mode
* Encoder position tracking
* Thickness computation pipeline
* Signal filtering
* Calibration support
* Alarm monitoring
* CSV/HDF5 logging
* Real-time visualization
* Modular industrial architecture

---

# Project Structure

```text
steel_thickness_system/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── constants.py
│   │
│   ├── sensors/
│   │   ├── sensor_manager.py
│   │   ├── simulation_loader.py
│   │   ├── frame.py
│   │   └── encoder_manager.py
│   │
│   ├── processing/
│   │   ├── thickness.py
│   │   ├── alignment.py
│   │   ├── filters.py
│   │   ├── statistics.py
│   │   └── cosine_correction.py
│   │
│   ├── filtering/
│   │   ├── gaussian_filter.py
│   │   ├── median_filter.py
│   │   └── temporal_filter.py
│   │
│   ├── pipeline/
│   │   ├── acquisition_pipeline.py
│   │   ├── processing_pipeline.py
│   │   └── threading_model.py
│   │
│   ├── export/
│   │   ├── csv_logger.py
│   │   ├── hd5_logger.py
│   │   └── report_generator.py
│   │
│   ├── visualization/
│   │   ├── live_plot.py
│   │   ├── plot_widgets.py
│   │   └── alarm_panel.py
│   │
│   ├── calibration/
│   │   ├── mastering_engine.py
│   │   └── calibration_io.py
│   │
│   ├── tests/
│   │   ├── test_alignment.py
│   │   ├── test_filters.py
│   │   └── test_thickness.py
│   │
│   └── utils/
│       ├── logger.py
│       ├── validator.py
│       └── timers.py
│
├── data/
├── logs/
├── calibration/
├── config.json
└── requirment.txt
```

---

# Installation

## 1. Clone or Extract the Project

```bash
unzip steel_thickness_system.zip
cd steel_thickness_system
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirment.txt
```

---

# CSV Simulation Mode

The system supports running using simulated CSV sensor data.

---

# Expected CSV Format

Your CSV file must contain:

```text
x,z
0.0,10.2
0.1,10.1
0.2,10.4
0.3,10.3
```

Where:

| Column | Description                 |
| ------ | --------------------------- |
| x      | Position / X coordinate     |
| z      | Sensor height / measurement |

---

# Place CSV File

Put your simulation CSV inside:

```text
/data/
```

Example:

```text
/data/sample_strip.csv
```

---

# Running CSV Simulation

## Step 1

Open:

```text
app/main.py
```

---

## Step 2

Add:

```python
from app.sensors.simulation_loader import SimulationLoader
```

---

## Step 3

Inside `main.py`:

```python
loader = SimulationLoader()
frame = loader.load_csv("data/sample_strip.csv")

print(frame.x)
print(frame.z)
```

---

# Full Example

Replace `app/main.py` temporarily with:

```python
from app.sensors.simulation_loader import SimulationLoader


def main():

    loader = SimulationLoader()

    frame = loader.load_csv("data/sample_strip.csv")

    print("CSV Loaded Successfully")

    print("Total Samples:", len(frame.x))

    print("First 10 Thickness Values:")

    print(frame.z[:10])


if __name__ == '__main__':
    main()
```

---

# Run the Project

```bash
python -m app.main
```

Expected Output:

```text
CSV Loaded Successfully
Total Samples: 5000
First 10 Thickness Values:
[10.2 10.1 10.4 ...]
```

---

# Real-Time Playback Simulation

You can simulate industrial streaming instead of loading all data at once.

Example:

```python
import time

for i in range(len(frame.x)):

    current_x = frame.x[i]
    current_z = frame.z[i]

    print(current_x, current_z)

    time.sleep(0.01)
```

This creates a 100 Hz streaming simulation.

---

# Recommended Industrial Thickness Formula

For dual laser sensors:

```text
Thickness = ReferenceGap - (TopSensor + BottomSensor)
```

Where:

* ReferenceGap = calibrated mechanical distance
* TopSensor = upper laser distance
* BottomSensor = lower laser distance

---

# Logging Output

Logs are saved in:

```text
/logs/
```

Supported formats:

* CSV
* HDF5

---

# Running Tests

```bash
pytest app/tests
```

---

# Recommended Future Improvements

## GUI

* PySide6
* PyQtGraph
* Real-time dashboards
* Alarm panels

## Industrial Features

* PLC communication
* OPC-UA integration
* Defect detection
* AI-based anomaly detection
* Multi-sensor fusion
* Database storage

---

# Recommended Technology Stack

| Component            | Technology |
| -------------------- | ---------- |
| GUI                  | PySide6    |
| Plotting             | PyQtGraph  |
| Storage              | HDF5       |
| Backend              | FastAPI    |
| AI                   | PyTorch    |
| Numerical Processing | NumPy      |
| Data Analysis        | Pandas     |

---

# Author

Developed as an industrial-style software architecture project for steel thickness monitoring and strip inspection systems.
