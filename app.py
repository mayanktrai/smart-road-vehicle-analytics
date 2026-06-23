from __future__ import annotations

"""Flask dashboard + live processing."""

import argparse
import logging
import time
import os
import sys
from pathlib import Path

# ─── RENDER PLATFORM PATH FIX (COMPLETE INJECTION) ────────────────────
# Yeh automatically script ke location aur uske parent directories ko add karega
script_dir = Path(__file__).resolve().parent
root_dir = script_dir.parent

if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Extra insurance: Agar Render 'src' folder ko nahi dekh pa raha hai
src_dir = script_dir / "src"
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
# ──────────────────────────────────────────────────────────────────────

from flask import Flask, Response, jsonify, render_template

# Har tarah ke folder layout ke liye fallback mechanisms
try:
    from src.config import Config
    from src.pipeline import Pipeline
except (ModuleNotFoundError, ImportError):
    try:
        from config import Config
        from pipeline import Pipeline
    except (ModuleNotFoundError, ImportError):
        # Agar absolute fail ho jaye toh system path standard import try karein
        import config as Config  # type: ignore
        import pipeline as Pipeline  # type: ignore

app = Flask(
    __name__,
    template_folder="dashboard/templates",
    static_folder="dashboard/static",
)
log = logging.getLogger("app")

pipeline: Pipeline = None  # type: ignore
config: Config = None      # type: ignore


def _mjpeg_generator():
    import cv2

    blank_sent = False
    while True:
        frame = pipeline.get_latest_frame()
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
        refresh_seconds=int(config.get("dashboard.refresh_seconds", 5)),
        speed_limit=config.get("speed.speed_limit_kmph", 60),
    )


@app.route("/video_feed")
def video_feed():
    return Response(
        _mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/stats")
def api_stats():
    live = pipeline.get_stats()
    summary = pipeline.db.summary()
    return jsonify({**live, **summary})


@app.route("/api/categories")
def api_categories():
    return jsonify(pipeline.db.counts_by_category())


@app.route("/api/hourly")
def api_hourly():
    return jsonify(pipeline.db.hourly_counts(hours=24))


@app.route("/api/violations")
def api_violations():
    return jsonify(pipeline.db.recent_violations(limit=20))


def main() -> None:
    global pipeline, config

    parser = argparse.ArgumentParser(description="Smart Road Vehicle Analytics dashboard")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = Config.load(args.config)
    pipeline = Pipeline(config)
    pipeline.start_async()

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", config.get("dashboard.port", 5000)))
    
    log.info("Dashboard on http://%s:%s", host, port)
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    main()