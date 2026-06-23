"""Congestion classification by ROI occupancy.

Traffic state is derived from the spatial ratio of vehicle bounding boxes to the
monitored road area (slide: Traffic Density Analysis). Returns Low / Medium / High
and a boolean alert flag for the High state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


def _polygon_area(poly: Sequence[Tuple[float, float]]) -> float:
    """Shoelace area of a polygon."""
    n = len(poly)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _point_in_poly(point, poly: Sequence[Tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    x, y = point
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
        ):
            inside = not inside
        j = i
    return inside


@dataclass
class DensityResult:
    occupancy: float
    state: str          # "Low" | "Medium" | "High"
    alert: bool


class DensityAnalyzer:
    def __init__(self, cfg) -> None:
        d = cfg.get("density", {}) or {}
        self.roi: List[Tuple[float, float]] = [tuple(p) for p in d.get("roi", [])]
        self.low_max = float(d.get("low_max", 0.15))
        self.high_min = float(d.get("high_min", 0.35))
        self._roi_area = _polygon_area(self.roi) if self.roi else 0.0

    def classify(self, detections) -> DensityResult:
        if self._roi_area <= 0:
            return DensityResult(occupancy=0.0, state="Low", alert=False)

        covered = 0.0
        for det in detections:
            if _point_in_poly(det.centroid, self.roi):
                covered += det.area

        occupancy = min(covered / self._roi_area, 1.0)
        if occupancy >= self.high_min:
            state, alert = "High", True
        elif occupancy <= self.low_max:
            state, alert = "Low", False
        else:
            state, alert = "Medium", False
        return DensityResult(occupancy=occupancy, state=state, alert=alert)
