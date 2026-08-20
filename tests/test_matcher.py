from __future__ import annotations

import numpy as np
import pytest

from attendance_system.face.matcher import FaceMatcher, GalleryEntry, select_kiosk_gallery


def test_identifies_similar_vector() -> None:
    enrolled = np.array([1.0, 0.0], dtype=np.float32)
    query = np.array([0.98, 0.2], dtype=np.float32)
    matcher = FaceMatcher([GalleryEntry("20260001", "Ana Perez Demo", enrolled)], 0.45)
    result = matcher.match(query)
    assert result.identified is True
    assert result.student_id == "20260001"
    assert result.score >= 0.45


def test_rejects_below_threshold_without_leaking_name() -> None:
    enrolled = np.array([1.0, 0.0], dtype=np.float32)
    query = np.array([0.0, 1.0], dtype=np.float32)
    matcher = FaceMatcher([GalleryEntry("20260001", "Ana Perez Demo", enrolled)], 0.45)
    result = matcher.match(query)
    assert result.identified is False
    assert result.full_name is None
    assert result.student_id is None
    assert result.label == "NO IDENTIFICADO"
    assert result.score == pytest.approx(0.0, abs=1e-5)


def test_empty_gallery_never_identifies() -> None:
    matcher = FaceMatcher([], 0.45)
    result = matcher.match(np.array([1.0, 0.0], dtype=np.float32))
    assert result.identified is False
    assert matcher.size == 0


def test_picks_the_closest_enrolled_face() -> None:
    ana = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    carlos = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    query = np.array([0.15, 0.98, 0.0], dtype=np.float32)
    matcher = FaceMatcher(
        [
            GalleryEntry("20260001", "Ana", ana),
            GalleryEntry("20260002", "Carlos", carlos),
        ],
        0.45,
    )
    result = matcher.match(query)
    assert result.identified is True
    assert result.student_id == "20260002"


def test_three_poses_of_same_person_use_best_angle() -> None:
    frente = np.array([1.0, 0.0], dtype=np.float32)
    lado = np.array([0.0, 1.0], dtype=np.float32)
    matcher = FaceMatcher(
        [
            GalleryEntry("20260001", "Ana", frente),
            GalleryEntry("20260001", "Ana", lado),
        ],
        0.45,
    )
    result = matcher.match(np.array([0.05, 0.99], dtype=np.float32))
    assert result.identified is True
    assert result.student_id == "20260001"
    assert matcher.person_count == 1
    assert matcher.size == 2


def test_kiosk_gallery_drops_demo_when_real_students_exist() -> None:
    ana = GalleryEntry("20260001", "Ana", np.array([1.0, 0.0], dtype=np.float32))
    real = GalleryEntry("TMP-0001", "Giovanny", np.array([0.0, 1.0], dtype=np.float32))
    selected = select_kiosk_gallery([ana, real])
    assert [item.student_id for item in selected] == ["TMP-0001"]


def test_kiosk_gallery_keeps_demo_if_nobody_else_is_enrolled() -> None:
    ana = GalleryEntry("20260001", "Ana", np.array([1.0, 0.0], dtype=np.float32))
    selected = select_kiosk_gallery([ana])
    assert [item.student_id for item in selected] == ["20260001"]
