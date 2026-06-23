"""Vehicle detection and tracking.

Wraps Ultralytics YOLOv8 with its built-in ByteTrack tracker so each detection
carries a persistent track_id across frames (slide: Detection + Tracking).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Detection:
    track_id: Optional[int]
    class_id: int
    name: str            # COCO class name, e.g. "car"
    category: str        # internal category, e.g. "LMV"
    confidence: float
    box: tuple           # (x1, y1, x2, y2) in pixels

    @property
    def centroid(self) -> tuple:
        x1, y1, x2, y2 = self.box
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)


class VehicleDetector:
    """YOLOv8 detector with ByteTrack tracking."""

    def __init__(self, cfg) -> None:
        from ultralytics import YOLO  # imported lazily so tests don't require it

        det = cfg["detector"]
        self.model = YOLO(det.get("model", "yolov8n.pt"))
        self.conf = float(det.get("conf", 0.35))
        self.iou = float(det.get("iou", 0.5))
        self.tracker = det.get("tracker", "bytetrack.yaml")
        self.device = det.get("device", "") or None

        # Normalise the class map keys to ints (YAML may load them as ints already).
        raw_map = det.get("class_map", {}) or {}
        self.class_map: Dict[int, Dict[str, str]] = {
            int(k): v for k, v in raw_map.items()
        }

    def track(self, frame):
        """Run detection + tracking on one frame, returning a list of Detection."""
        results = self.model.track(
            frame,
            persist=True,
            conf=self.conf,
            iou=self.iou,
            tracker=self.tracker,
            device=self.device,
            verbose=False,
        )
        return self._parse(results)

    def _parse(self, results) -> List[Detection]:
        detections: List[Detection] = []
        if not results:
            return detections
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            # No tracked objects this frame.
            return detections

        ids = boxes.id.int().cpu().tolist()
        clss = boxes.cls.int().cpu().tolist()
        confs = boxes.conf.float().cpu().tolist()
        xyxy = boxes.xyxy.cpu().tolist()

        for track_id, cls_id, conf, box in zip(ids, clss, confs, xyxy):
            mapping = self.class_map.get(int(cls_id))
            if mapping is None:
                continue  # not a vehicle class we care about
            detections.append(
                Detection(
                    track_id=int(track_id),
                    class_id=int(cls_id),
                    name=mapping.get("name", str(cls_id)),
                    category=mapping.get("category", "Unknown"),
                    confidence=float(conf),
                    box=tuple(float(v) for v in box),
                )
            )
        return detections
