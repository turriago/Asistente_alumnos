from __future__ import annotations

import numpy as np
import pytest

from attendance_system.drawing import draw_faces
from attendance_system.face.detector import parse_yunet_faces
from attendance_system.face.embedder import yunet_row
from attendance_system.face.model import FaceModelError, ensure_sface_model, ensure_yunet_model
from attendance_system.face.types import DetectedFace


def _row(
    x: float,
    y: float,
    width: float,
    height: float,
    score: float,
    landmarks: tuple[tuple[float, float], ...] | None = None,
) -> list[float]:
    points = landmarks or ((10, 10), (20, 10), (15, 20), (12, 28), (18, 28))
    values = [x, y, width, height]
    for px, py in points:
        values.extend([px, py])
    values.append(score)
    return values


def test_parse_none_and_empty() -> None:
    assert parse_yunet_faces(None, score_threshold=0.7, min_face_size=40) == []
    assert parse_yunet_faces(np.zeros((0, 15)), score_threshold=0.7, min_face_size=40) == []


def test_parse_keeps_face_above_threshold() -> None:
    raw = np.array([_row(10, 20, 80, 90, 0.92)], dtype=np.float32)
    faces = parse_yunet_faces(raw, score_threshold=0.7, min_face_size=40)
    assert len(faces) == 1
    face = faces[0]
    assert face.x == 10
    assert face.y == 20
    assert face.width == 80
    assert face.height == 90
    assert face.score == pytest.approx(0.92)
    assert len(face.landmarks) == 5


def test_parse_filters_low_score() -> None:
    raw = np.array([_row(10, 20, 80, 90, 0.2)], dtype=np.float32)
    faces = parse_yunet_faces(raw, score_threshold=0.7, min_face_size=40)
    assert faces == []


def test_parse_filters_small_face() -> None:
    raw = np.array([_row(10, 20, 20, 20, 0.99)], dtype=np.float32)
    faces = parse_yunet_faces(raw, score_threshold=0.7, min_face_size=40)
    assert faces == []


def test_parse_sorts_by_area() -> None:
    raw = np.array(
        [
            _row(0, 0, 50, 50, 0.9),
            _row(10, 10, 100, 120, 0.8),
        ],
        dtype=np.float32,
    )
    faces = parse_yunet_faces(raw, score_threshold=0.5, min_face_size=40)
    assert [face.width for face in faces] == [100, 50]


def test_parse_ignores_short_rows() -> None:
    raw = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
    assert parse_yunet_faces(raw, score_threshold=0.1, min_face_size=1) == []


def test_resize_and_scale_faces_roundtrip() -> None:
    from attendance_system.face.detector import resize_for_yunet, scale_faces

    huge = np.zeros((4000, 5328, 3), dtype=np.uint8)
    small, scale = resize_for_yunet(huge, max_side=1600)
    assert max(small.shape[:2]) == 1600
    assert scale < 1
    face = DetectedFace(x=10, y=20, width=80, height=90, score=0.9, landmarks=((12, 22),))
    mapped = scale_faces([face], scale)[0]
    assert mapped.x == int(round(10 / scale))
    tiny = np.zeros((480, 640, 3), dtype=np.uint8)
    same, one = resize_for_yunet(tiny, max_side=1600)
    assert one == 1.0
    assert same.shape == tiny.shape


def test_draw_faces_does_not_crash() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    face = DetectedFace(
        x=40,
        y=30,
        width=80,
        height=90,
        score=0.88,
        landmarks=((50, 50), (90, 50), (70, 70), (55, 95), (85, 95)),
    )
    drawn = draw_faces(frame, [face], draw_landmarks=True)
    assert drawn.shape == frame.shape
    assert not np.array_equal(drawn, frame)


def test_missing_model_without_download(tmp_path) -> None:
    with pytest.raises(FaceModelError, match="YuNet"):
        ensure_yunet_model(tmp_path / "missing.onnx", auto_download=False)


def test_missing_sface_without_download(tmp_path) -> None:
    with pytest.raises(FaceModelError, match="SFace"):
        ensure_sface_model(tmp_path, auto_download=False)


def test_yunet_row_matches_detector_layout() -> None:
    face = DetectedFace(
        x=12,
        y=20,
        width=80,
        height=90,
        score=0.91,
        landmarks=((14, 30), (70, 32), (42, 55), (20, 88), (65, 90)),
    )
    row = yunet_row(face)
    assert row.shape == (15,)
    parsed = parse_yunet_faces(row.reshape(1, -1), score_threshold=0.5, min_face_size=40)
    assert len(parsed) == 1
    assert parsed[0].x == face.x
    assert parsed[0].score == pytest.approx(face.score)
    assert parsed[0].landmarks == face.landmarks
