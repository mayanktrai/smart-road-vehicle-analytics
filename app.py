"""Flask dashboard + live processing.

Starts the analytics pipeline in a background thread, streams the annotated frames
as MJPEG, and serves JSON endpoints that the dashboard polls for charts and tables.

Usage:
    python app.py --config config.yaml
    # then open http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
import logging
import time

from flask import Flask, Response, jsonify, render_template

from src.config import Config
from src.pipeline import Pipeline

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

    host = config.get("dashboard.host", "127.0.0.1")
    port = int(config.get("dashboard.port", 5000))
    log.info("Dashboard on http://%s:%s", host, port)
    # threaded=True so the MJPEG stream doesn't block API calls.
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
