"""Tipos de detección de manos. El recuento 1–10 vive en fingers.py."""

from __future__ import annotations

from dataclasses import dataclass

# Esqueleto MediaPipe Hands (21 puntos). Sin copiar código de terceros.
HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)


@dataclass(frozen=True)
class DetectedHand:
    landmarks: tuple[tuple[int, int], ...]
    handedness: str
    score: float
    world: tuple[tuple[float, float, float], ...] = ()

    def swapped_handedness(self) -> DetectedHand:
        if self.handedness == "Left":
            name = "Right"
        elif self.handedness == "Right":
            name = "Left"
        else:
            name = self.handedness
        return DetectedHand(
            landmarks=self.landmarks,
            handedness=name,
            score=self.score,
            world=self.world,
        )
