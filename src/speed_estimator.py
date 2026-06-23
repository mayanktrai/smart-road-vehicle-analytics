"""Speed estimation.

Implements the deck's logic: a homography maps perspective image pixels to metric
distances on the road plane, then for each track the metric displacement between
samples gives speed via

    v = (displacement_d * frame_rate_fps) / frame_count_delta_f

i.e. metres-per-frame * fps = metres-per-second, scaled to km/h. Speeds above the
configured lane limit are flagged (slide: Speed Estimation Logic).
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple


@dataclass
class SpeedSample:
    frame_idx: int
    point_m: Tuple[float, float]  # position in metres (road plane)


@dataclass
class SpeedResult:
    track_id: int
    speed_kmph: float
    is_violation: bool


def build_homography(image_points, zone_length_m: float, zone_width_m: float):
    """Map the four image_points (TL, TR, BR, BL) to a metric rectangle.

    The destination rectangle is width=zone_width_m, height=zone_length_m, so the
    transformed coordinates are directly in metres.
    """
    import cv2
    import numpy as np

    src = np.array(image_points, dtype="float32")
    dst = np.array(
        [
            [0.0, 0.0],
            [zone_width_m, 0.0],
            [zone_width_m, zone_length_m],
            [0.0, zone_length_m],
        ],
        dtype="float32",
    )
    return cv2.getPerspectiveTransform(src, dst)


class SpeedEstimator:
    def __init__(self, cfg, fps: float) -> None:
        sp = cfg.get("speed", {}) or {}
        self.enabled = bool(sp.get("enabled", True))
        self.fps = float(fps) if fps and fps > 0 else 30.0
        self.limit = float(sp.get("speed_limit_kmph", 60))
        self.min_points = int(sp.get("min_track_points", 4))
        self.smoothing = int(sp.get("smoothing", 3))
        self._H = None
        if self.enabled and sp.get("image_points"):
            self._H = build_homography(
                sp["image_points"],
                float(sp.get("zone_length_m", 20.0)),
                float(sp.get("zone_width_m", 7.0)),
            )
        self._history: Dict[int, Deque[SpeedSample]] = defaultdict(
            lambda: deque(maxlen=max(self.min_points + self.smoothing, 8))
        )
        self._reported: set = set()

    def _to_metres(self, point) -> Tuple[float, float]:
        if self._H is None:
            return (float(point[0]), float(point[1]))
        import numpy as np

        vec = np.array([point[0], point[1], 1.0], dtype="float64")
        out = self._H @ vec
        out /= out[2]
        return (float(out[0]), float(out[1]))

    def update(self, track_id: int, centroid, frame_idx: int) -> Optional[SpeedResult]:
        """Feed a tracked centroid; return a SpeedResult once stable, else None."""
        if not self.enabled or track_id is None:
            return None

        hist = self._history[track_id]
        hist.append(SpeedSample(frame_idx, self._to_metres(centroid)))
        if len(hist) < self.min_points:
            return None

        speeds: List[float] = []
        samples = list(hist)
        for prev, cur in zip(samples[:-1], samples[1:]):
            delta_f = cur.frame_idx - prev.frame_idx
            if delta_f <= 0:
                continue
            d = math.dist(prev.point_m, cur.point_m)  # metres
            mps = (d * self.fps) / delta_f             # v = d * fps / Δf
            speeds.append(mps * 3.6)                    # -> km/h

        if not speeds:
            return None

        window = speeds[-self.smoothing :] if self.smoothing > 0 else speeds
        speed_kmph = sum(window) / len(window)
        is_violation = speed_kmph > self.limit
        return SpeedResult(track_id=track_id, speed_kmph=speed_kmph, is_violation=is_violation)

    def already_reported(self, track_id: int) -> bool:
        return track_id in self._reported

    def mark_reported(self, track_id: int) -> None:
        self._reported.add(track_id)
