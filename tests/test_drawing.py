from __future__ import annotations

import numpy as np
import pytest

from attendance_system.drawing import draw_faces, draw_overlay
from attendance_system.face.types import DetectedFace
from attendance_system.text import draw_texts, resolve_ui_font_path


def test_overlay_renders_spanish_accents() -> None:
    if resolve_ui_font_path() is None:
        pytest.skip("No hay fuente TTF con tildes en este sistema.")
    blank = np.full((90, 320, 3), 18, dtype=np.uint8)
    with_accent = draw_texts(blank.copy(), [("Pérez", (24, 60), (255, 255, 255), 32, 1)])
    without = draw_texts(blank.copy(), [("Perez", (24, 60), (255, 255, 255), 32, 1)])
    assert with_accent.sum() > blank.sum()
    assert not np.array_equal(with_accent, without)


def test_draw_overlay_and_face_label_utf8() -> None:
    frame = np.zeros((240, 400, 3), dtype=np.uint8)
    overlay = draw_overlay(frame, ["Galería: 1", "Ana Pérez Demo"])
    assert overlay.shape == frame.shape
    assert not np.array_equal(overlay, frame)
    face = DetectedFace(
        x=40,
        y=80,
        width=80,
        height=90,
        score=0.9,
        landmarks=((50, 90), (90, 90), (70, 110), (55, 140), (85, 140)),
    )
    labeled = draw_faces(frame, [face], labels=["Ana Pérez Demo 0.76"], identified=True)
    assert labeled.shape == frame.shape


def test_face_iou_overlap_and_disjoint() -> None:
    a = DetectedFace(x=0, y=0, width=50, height=50, score=1.0, landmarks=())
    same = DetectedFace(x=0, y=0, width=50, height=50, score=1.0, landmarks=())
    far = DetectedFace(x=80, y=80, width=20, height=20, score=1.0, landmarks=())
    assert a.iou(same) == pytest.approx(1.0)
    assert a.iou(far) == pytest.approx(0.0)
