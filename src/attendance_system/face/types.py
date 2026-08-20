"""Tipos de detección facial. Sin identidad."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DetectedFace:
    x: int
    y: int
    width: int
    height: int
    score: float
    landmarks: tuple[tuple[int, int], ...]

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    def crop(self, frame: np.ndarray, pad: float = 0.2) -> np.ndarray:
        height, width = frame.shape[:2]
        extra_x = int(self.width * pad)
        extra_y = int(self.height * pad)
        x1 = max(0, self.x - extra_x)
        y1 = max(0, self.y - extra_y)
        x2 = min(width, self.x + self.width + extra_x)
        y2 = min(height, self.y + self.height + extra_y)
        if x2 <= x1 or y2 <= y1:
            return np.zeros((1, 1, 3), dtype=frame.dtype)
        return frame[y1:y2, x1:x2].copy()

    def iou(self, other: DetectedFace) -> float:
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = self.area + other.area - inter
        if union <= 0:
            return 0.0
        return inter / union
