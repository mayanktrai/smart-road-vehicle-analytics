"""Line-crossing vehicle counter.

A vehicle is counted the first time its centroid crosses the virtual line segment.
The side of the line (computed by the sign of the 2D cross product) determines the
direction, so the two opposing flows are counted separately. Each track_id is counted
at most once (slide: Counting — centroid crossings against virtual ROI barriers).
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple


def _side(line_a, line_b, point) -> float:
    """Signed area / cross product: >0 one side, <0 the other, 0 on the line."""
    ax, ay = line_a
    bx, by = line_b
    px, py = point
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


class LineCounter:
    def __init__(self, line: Tuple[Tuple[float, float], Tuple[float, float]]) -> None:
        self.a, self.b = tuple(line[0]), tuple(line[1])
        self._last_side: Dict[int, float] = {}
        self._counted: set = set()
        self.count_up = 0    # negative -> positive crossings
        self.count_down = 0  # positive -> negative crossings

    @property
    def total(self) -> int:
        return self.count_up + self.count_down

    def update(self, track_id: Optional[int], centroid) -> Optional[str]:
        """Feed one tracked centroid. Returns 'up'/'down' on a crossing else None."""
        if track_id is None or track_id in self._counted:
            return None

        current = _side(self.a, self.b, centroid)
        previous = self._last_side.get(track_id)
        self._last_side[track_id] = current

        if previous is None or previous == 0:
            return None

        # Sign change between frames => the segment was crossed.
        if (previous < 0) and (current > 0):
            self.count_up += 1
            self._counted.add(track_id)
            return "up"
        if (previous > 0) and (current < 0):
            self.count_down += 1
            self._counted.add(track_id)
            return "down"
        return None
