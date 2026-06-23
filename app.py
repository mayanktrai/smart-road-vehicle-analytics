from __future__ import annotations

"""Flask dashboard + live processing.

Starts the analytics pipeline in a background thread, streams the annotated frames
as MJPEG, and serves JSON endpoints that the dashboard polls for charts and tables.
"""

import argparse
import logging
import os
import sys
import time

# ─── THE ULTIMATE BRUTE-FORCE PATH SCANNER ────────────────────────────
# Hum manually scan karke search paths register karenge taaki zero configuration defaults milein
_HERE = os.path.dirname(os.path.abspath(__file__))

# 1. Base files location system path me add karein
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 2. Agar Render ne folders nested kar diye hain, toh check karein ki 'src' folder kahan chhupa hai
_SRC_PATH_DIRECT = os.path.join(_HERE, "src")
_SRC_PATH_PARENT = os.path.join(os.path.dirname(_HERE), "src")

if os.path.exists(_SRC_PATH_DIRECT) and _SRC_PATH_DIRECT not in sys.path:
    sys.path.insert(0, _SRC_PATH_DIRECT)
if os.path.exists(_SRC_PATH_PARENT) and _SRC_PATH_PARENT not in sys.path:
    sys.path.insert(0, _SRC_PATH_PARENT)

# 3. Agar fir bhi fallback layer me custom module execution handle karna pade
sys.path.insert(0, os.path.dirname(_HERE))
# ──────────────────────────────────────────────────────────────────────

from flask import Flask, Response, jsonify, render_template

# Ab dynamic framework wrapper module loading chalegi bina crash huye
try:
    from src.config import Config
    from src.pipeline import Pipeline
except (ModuleNotFoundError, ImportError):
    try:
        import config as Config  # type: ignore
        import pipeline as Pipeline  # type: ignore
    except (ModuleNotFoundError, ImportError):
        try:
            from config import Config  # type: ignore
            from pipeline import Pipeline  # type: ignore
        except (ModuleNotFoundError, ImportError) as err:
            # Taaki exact debugging directory output dikhe agar absolute failure ho
            print(f"CRITICAL DEBUG INFO: Current sys.path is {sys.path}", flush=True)
            print(f"CRITICAL DEBUG INFO: Current directory content is {os.listdir(_HERE)}", flush=True)
            raise err

# UI-only mode escape hatch for memory-constrained hosts.
RUN_PIPELINE = os.environ.get("RUN_PIPELINE", "1") != "0"

app = Flask(
    __name__,
    template_folder="dashboard/templates",
    static_folder="dashboard/static",
)
log = logging.getLogger("app")

pipeline: Pipeline | None = None
config: Config | None = None


def _mjpeg_generator():
    import cv2

    blank_sent = False
    while True:
        frame = pipeline.get_latest_frame() if pipeline is not None else None
        if frame is None:
            if not blank_sent:
                time.sleep(0.1)
            blank_sent = True
            continue
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )
        time.sleep(0.03)  # ~30 fps cap for the browser


@app.route("/")
def index():
    return render_template(
        "index.html",
        refresh_seconds=int(config.get("dashboard.refresh_seconds", 5)) if config else 5,
        speed_limit=config.get("speed.speed_limit_kmph", 60) if config else 60,
    )


@app.route("/video_feed")
def video_feed():
    if pipeline is None:
        return Response(
            "Live processing is disabled (RUN_PIPELINE=0).",
            status=503,
            mimetype="text/plain",
        )
    return Response(
        _mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/stats")
def api_stats():
    if pipeline is None:
        return jsonify(
            {
                "count_up": 0,
                "count_down": 0,
                "total": 0,
                "density_state": "-",
                "occupancy": 0.0,
                "fps": 0.0,
                "total_vehicles": 0,
                "total_violations": 0,
                "total_plates": 0,
            }
        )
    live = pipeline.get_stats()
    summary = pipeline.db.summary()
    return jsonify({**live, **summary})


@app.route("/api/categories")
def api_categories():
    return jsonify(pipeline.db.counts_by_category() if pipeline is not None else {})


@app.route("/api/hourly")
def api_hourly():
    return jsonify(pipeline.db.hourly_counts(hours=24) if pipeline is not None else [])


@app.route("/api/violations")
def api_violations():
    return jsonify(pipeline.db.recent_violations(limit=20) if pipeline is not None else [])


def main() -> None:
    global pipeline, config

    parser = argparse.ArgumentParser(description="Smart Road Vehicle Analytics dashboard")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Config location loading block safely
    try:
        config = Config.load(args.config)
    except Exception:
        config_path = os.path.join(_HERE, args.config)
        config = Config.load(config_path)

    if RUN_PIPELINE:
        try:
            pipeline = Pipeline(config)
            pipeline.start_async()
        except Exception as exc:  # keep the dashboard up even if the pipeline can't start
            log.error("Could not start pipeline (%s); serving dashboard UI only.", exc)
            pipeline = None
    else:
        log.info("RUN_PIPELINE=0 — serving dashboard UI only (no video processing).")

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", config.get("dashboard.port", 5000)))
    log.info("Dashboard on http://%s:%s", host, port)
    
    # threaded=True so the MJPEG stream doesn't block API calls.
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
