"""End-to-end processing pipeline.

Orchestrates: frame acquisition -> detection+tracking -> counting -> speed estimation
-> ANPR -> congestion -> annotated overlay -> MySQL logging. Exposes the latest
annotated frame and live stats so the Flask app can stream and chart them.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional

from .anpr import ANPR
from .counter import LineCounter
from .database import Database
from .density import DensityAnalyzer
from .detector import VehicleDetector
from .speed_estimator import SpeedEstimator

log = logging.getLogger("pipeline")

# Box colours (BGR) per category.
CATEGORY_COLORS = {
    "LMV": (0, 200, 0),
    "HMV": (0, 140, 255),
    "Two-Wheeler": (255, 160, 0),
    "Unknown": (180, 180, 180),
}


class Pipeline:
    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.source = cfg["source"]
        self.process_every_n = int(cfg.get("process_every_n", 1))
        self.output_path = cfg.get("output_path", "")

        self.detector = VehicleDetector(cfg)
        self.counter = LineCounter(tuple(map(tuple, cfg["counter"]["line"])))
        self.density = DensityAnalyzer(cfg)
        self.anpr = ANPR(cfg)
        self.db = Database(cfg)
        self.speed_limit = float(cfg.get("speed.speed_limit_kmph", 60))

        # Live state for the dashboard.
        self._lock = threading.Lock()
        self._latest_frame = None
        self.stats: Dict = {
            "count_up": 0,
            "count_down": 0,
            "total": 0,
            "density_state": "Low",
            "occupancy": 0.0,
            "fps": 0.0,
        }
        self._stop = threading.Event()
        self._seen_db_ids: Dict[int, int] = {}  # track_id -> vehicles.id

    # ---- drawing ----------------------------------------------------------
    def _annotate(self, frame, detections, density_result):
        import cv2

        a, b = self.counter.a, self.counter.b
        cv2.line(frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (0, 0, 255), 2)

        for det in detections:
            x1, y1, x2, y2 = (int(v) for v in det.box)
            color = CATEGORY_COLORS.get(det.category, CATEGORY_COLORS["Unknown"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{det.category} #{det.track_id}"
            cv2.putText(
                frame, label, (x1, max(y1 - 6, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
            )

        banner = (
            f"Up:{self.counter.count_up}  Down:{self.counter.count_down}  "
            f"Total:{self.counter.total}  Density:{density_result.state} "
            f"({density_result.occupancy:.0%})"
        )
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 30), (32, 32, 32), -1)
        cv2.putText(
            frame, banner, (10, 21),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA,
        )
        return frame

    # ---- per-frame --------------------------------------------------------
    def _handle_detection(self, frame, det, speed_estimator, frame_idx):
        """Counting, speed, ANPR and DB logging for one detection."""
        crossing = self.counter.update(det.track_id, det.centroid)

        # Persist the vehicle row once (on first sight / first crossing).
        if det.track_id not in self._seen_db_ids and crossing is not None:
            vid = self.db.insert_vehicle(
                det.track_id, det.category, det.name, det.confidence
            )
            if vid is not None:
                self._seen_db_ids[det.track_id] = vid

        # Speed.
        if speed_estimator.enabled:
            result = speed_estimator.update(det.track_id, det.centroid, frame_idx)
            if (
                result is not None
                and result.is_violation
                and not speed_estimator.already_reported(det.track_id)
            ):
                speed_estimator.mark_reported(det.track_id)
                vid = self._seen_db_ids.get(det.track_id)
                if vid is None:
                    vid = self.db.insert_vehicle(
                        det.track_id, det.category, det.name, det.confidence
                    )
                    if vid is not None:
                        self._seen_db_ids[det.track_id] = vid
                if vid is not None:
                    self.db.insert_violation(vid, result.speed_kmph, self.speed_limit)

                # ANPR on the offending vehicle crop.
                if self.anpr.enabled:
                    x1, y1, x2, y2 = (int(v) for v in det.box)
                    crop = frame[max(y1, 0):y2, max(x1, 0):x2]
                    plate = self.anpr.read(crop)
                    if plate is not None:
                        self.db.insert_anpr(vid, plate.text, plate.confidence)

    # ---- run loop ---------------------------------------------------------
    def run(self) -> None:
        import cv2

        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {self.source}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        speed_estimator = SpeedEstimator(self.cfg, fps=fps)

        writer = None
        if self.output_path:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))

        frame_idx = 0
        t0 = time.time()
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    break
                frame_idx += 1
                if frame_idx % self.process_every_n != 0:
                    continue

                detections = self.detector.track(frame)
                for det in detections:
                    self._handle_detection(frame, det, speed_estimator, frame_idx)

                density_result = self.density.classify(detections)
                annotated = self._annotate(frame, detections, density_result)

                if writer is not None:
                    writer.write(annotated)

                elapsed = time.time() - t0
                with self._lock:
                    self._latest_frame = annotated
                    self.stats.update(
                        {
                            "count_up": self.counter.count_up,
                            "count_down": self.counter.count_down,
                            "total": self.counter.total,
                            "density_state": density_result.state,
                            "occupancy": round(density_result.occupancy, 3),
                            "fps": round(frame_idx / elapsed, 1) if elapsed > 0 else 0.0,
                        }
                    )
        finally:
            cap.release()
            if writer is not None:
                writer.release()
            self.db.close()
            log.info("Pipeline finished: %d frames, %d vehicles counted.",
                     frame_idx, self.counter.total)

    # ---- threading helpers (used by the Flask app) ------------------------
    def start_async(self) -> threading.Thread:
        thread = threading.Thread(target=self._run_guarded, daemon=True)
        thread.start()
        return thread

    def _run_guarded(self) -> None:
        try:
            self.run()
        except Exception as exc:  # pragma: no cover
            log.error("Pipeline crashed: %s", exc)

    def stop(self) -> None:
        self._stop.set()

    def get_latest_frame(self):
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def get_stats(self) -> Dict:
        with self._lock:
            return dict(self.stats)
