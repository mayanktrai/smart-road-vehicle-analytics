# Smart Road Vehicle Analytics and Traffic Monitoring System

AI-driven traffic monitoring pipeline that detects, classifies, tracks, and analyses
vehicles from a live camera feed (RTSP/RTMP/file), estimates speed, reads number plates
(ANPR), classifies congestion, and persists structured logs to MySQL. A Flask dashboard
shows the live annotated stream plus real-time charts.

> MCA Major Project — Smart Road Vehicle Analytics and Traffic Monitoring System Using AI.

## What the system does

| Capability        | Module                  | Notes |
|-------------------|-------------------------|-------|
| Detect & classify | `src/detector.py`       | YOLOv8 → vehicles mapped to LMV / HMV / Two-Wheeler |
| Track             | `src/detector.py`       | ByteTrack track IDs persisted across frames |
| Count             | `src/counter.py`        | Centroid line-crossing counter, per-direction |
| Speed             | `src/speed_estimator.py`| Homography + `v = d·FPS / Δf`, flags over-speed |
| ANPR              | `src/anpr.py`           | Plate localization → binarization → Tesseract OCR |
| Congestion        | `src/density.py`        | ROI occupancy ratio → Low / Medium / High |
| Storage           | `src/database.py`       | MySQL: `vehicles`, `speed_violations`, `anpr_logs` |
| Dashboard         | `app.py` + `dashboard/` | Flask + Plotly: live feed, counts, violations |

## Architecture

```
 Camera (RTSP/RTMP/file)
        │  frame
        ▼
 Detector (YOLOv8) ──► Tracker (ByteTrack)
        │ detections + track_ids
        ▼
 ┌──────────────┬──────────────┬───────────────┬──────────────┐
 │  Counter     │ SpeedEstim.  │   ANPR        │  Density      │
 └──────────────┴──────────────┴───────────────┴──────────────┘
        │ logs
        ▼
 MySQL  ◄────────────────────────────────►  Flask API + Plotly dashboard
```

## Setup

1. Python 3.9+ and (optional) a CUDA GPU for real-time FPS.
2. Install Tesseract OCR (system package) for ANPR:
   - Ubuntu: `sudo apt install tesseract-ocr`
   - Windows: install from UB-Mannheim build, set path in `config.yaml`.
3. Install Python deps:
   ```bash
   pip install -r requirements.txt
   ```
4. Create the database:
   ```bash
   mysql -u root -p < schema.sql
   ```
5. Put a YOLOv8 model in `models/` (e.g. `yolov8n.pt`; downloaded automatically by
   Ultralytics on first run). For dedicated plate detection, add a plate model and set
   `anpr.plate_model` in `config.yaml` (optional — falls back to a contour heuristic).

## Configure

Edit `config.yaml`: video `source`, the counting `line`, the speed-zone `homography`
points and real-world `zone_length_m`, the `speed_limit_kmph`, the congestion ROI, and
your MySQL credentials.

## Run

Pipeline only (writes annotated video + logs to DB):
```bash
python run_detection.py --config config.yaml
```

Dashboard + live processing together:
```bash
python app.py --config config.yaml
# open http://127.0.0.1:5000
```

## Tests

```bash
pytest -q
```

Unit tests cover the speed formula, the line-crossing counter, and congestion
classification. `tests/test_database.py` uses a mock connection so it runs without a
live MySQL server.

## Notes / limitations

- Speed accuracy depends on a correct homography calibration of the measurement zone;
  the four `homography.image_points` must map to a real rectangle of known size on the road.
- ANPR accuracy depends on plate resolution; OCR is best-effort and post-filtered with a
  plate regex. Swap in a trained plate-detection model for production use.
- COCO-pretrained YOLOv8 has no `license_plate` class, so plate localization is a
  contour heuristic unless you supply `anpr.plate_model`.
