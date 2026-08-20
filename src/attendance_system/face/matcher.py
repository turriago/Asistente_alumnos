"""Comparación de embeddings por similitud coseno. Sin asistencia ni liveness."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from attendance_system.face.embedder import l2_normalize


@dataclass(frozen=True)
class GalleryEntry:
    student_id: str
    full_name: str
    embedding: np.ndarray
    program: str = ""
    group_name: str = ""


@dataclass(frozen=True)
class MatchResult:
    identified: bool
    student_id: str | None
    full_name: str | None
    score: float
    threshold: float
    program: str | None = None
    group_name: str | None = None

    @property
    def label(self) -> str:
        if self.identified and self.full_name:
            return f"{self.full_name} ({self.student_id})"
        return "NO IDENTIFICADO"


SAMPLE_DEMO_IDS = frozenset(
    {"20260001", "20260002", "20260003", "20260004", "20260005"}
)


def select_kiosk_gallery(entries: list[GalleryEntry]) -> list[GalleryEntry]:
    """Si hay estudiantes reales enrolados, no uses las caras ficticias de demo."""
    real = [item for item in entries if item.student_id not in SAMPLE_DEMO_IDS]
    return real if real else list(entries)


class FaceMatcher:
    """1:N contra la galería en RAM. El umbral sale de la config, no del código."""

    def __init__(self, entries: list[GalleryEntry], threshold: float) -> None:
        if not 0 <= threshold <= 1:
            raise ValueError("El umbral de matching debe estar entre 0 y 1.")
        self.threshold = float(threshold)
        self.entries = entries
        if entries:
            matrix = np.stack([l2_normalize(item.embedding) for item in entries])
        else:
            matrix = np.zeros((0, 1), dtype=np.float32)
        self._matrix = matrix

    @property
    def size(self) -> int:
        return len(self.entries)

    @property
    def person_count(self) -> int:
        return len({item.student_id for item in self.entries})

    def match(self, query: np.ndarray) -> MatchResult:
        if self.size == 0:
            return MatchResult(
                identified=False,
                student_id=None,
                full_name=None,
                score=0.0,
                threshold=self.threshold,
            )
        vector = l2_normalize(query)
        scores = self._matrix @ vector
        best_index = int(np.argmax(scores))
        best_score = float(np.clip(scores[best_index], -1.0, 1.0))
        if best_score >= self.threshold:
            winner = self.entries[best_index]
            return MatchResult(
                identified=True,
                student_id=winner.student_id,
                full_name=winner.full_name,
                score=best_score,
                threshold=self.threshold,
                program=winner.program or None,
                group_name=winner.group_name or None,
            )
        return MatchResult(
            identified=False,
            student_id=None,
            full_name=None,
            score=best_score,
            threshold=self.threshold,
        )
