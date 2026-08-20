from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from attendance_system.face.matcher import FaceMatcher, GalleryEntry, MatchResult
from attendance_system.face.types import DetectedFace
from attendance_system.kiosk.app import create_app
from attendance_system.kiosk.engine import encode_jpeg
from attendance_system.kiosk.status import NEXT_STEP_PLACEHOLDER, build_status


def _face() -> DetectedFace:
    return DetectedFace(
        x=10,
        y=10,
        width=80,
        height=90,
        score=0.9,
        landmarks=((20, 20), (70, 20), (45, 50), (25, 80), (65, 80)),
    )


def test_status_waiting_and_unknown_hide_name() -> None:
    matcher = FaceMatcher(
        [GalleryEntry("20260001", "Ana Pérez Demo", np.array([1.0, 0.0], dtype=np.float32))],
        0.45,
    )
    waiting = build_status(
        faces=[],
        matcher=matcher,
        result=None,
        fps=12.0,
        dark=False,
        demo_mode=True,
        camera_ok=True,
    )
    assert waiting.state == "waiting"
    assert waiting.full_name is None
    unknown = build_status(
        faces=[_face()],
        matcher=matcher,
        result=MatchResult(False, None, None, 0.2, 0.45),
        fps=12.0,
        dark=False,
        demo_mode=True,
        camera_ok=True,
    )
    assert unknown.state == "unknown"
    assert unknown.full_name is None
    assert unknown.headline == "Estudiante no identificado"


def test_status_identified_includes_card_fields() -> None:
    matcher = FaceMatcher(
        [
            GalleryEntry(
                "20260001",
                "Ana Pérez Demo",
                np.array([1.0, 0.0], dtype=np.float32),
                program="Ingeniería de Sistemas",
                group_name="A",
            )
        ],
        0.45,
    )
    result = matcher.match(np.array([1.0, 0.0], dtype=np.float32))
    status = build_status(
        faces=[_face()],
        matcher=matcher,
        result=result,
        fps=18.3,
        dark=False,
        demo_mode=True,
        camera_ok=True,
    )
    assert status.state == "identified"
    assert status.student_id == "20260001"
    assert status.full_name == "Ana Pérez Demo"
    assert status.program == "Ingeniería de Sistemas"
    assert status.photo_url == "/api/photo/20260001"
    assert status.hands == 0
    assert status.gesture_number is None
    assert status.can_start_test is True
    assert "Iniciar prueba" in status.next_step


def test_status_identifies_largest_face_when_several_appear() -> None:
    matcher = FaceMatcher(
        [GalleryEntry("20260001", "Ana Pérez Demo", np.array([1.0, 0.0], dtype=np.float32))],
        0.45,
    )
    result = matcher.match(np.array([1.0, 0.0], dtype=np.float32))
    small = DetectedFace(
        x=200,
        y=10,
        width=30,
        height=30,
        score=0.8,
        landmarks=((205, 15), (220, 15), (212, 22), (208, 32), (218, 32)),
    )
    status = build_status(
        faces=[_face(), small],
        matcher=matcher,
        result=result,
        fps=15.0,
        dark=False,
        demo_mode=True,
        camera_ok=True,
    )
    assert status.state == "identified"
    assert status.faces == 2
    assert status.student_id == "20260001"
    assert "más cercano" in status.headline


class FakeEngine:
    def __init__(self) -> None:
        self.started = False
        self.reset = False

    def latest_jpeg(self) -> bytes:
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        return encode_jpeg(frame, 80)

    def latest_status(self):
        matcher = FaceMatcher([], 0.45)
        return build_status(
            faces=[],
            matcher=matcher,
            result=None,
            fps=0.0,
            dark=False,
            demo_mode=True,
            camera_ok=True,
        )

    def start_challenge(self) -> dict[str, object]:
        self.started = True
        return {"ok": False, "error": "Identifícate primero."}

    def reset_scan(self) -> dict[str, object]:
        self.reset = True
        return {"ok": True}


def test_kiosk_http_without_camera() -> None:
    client = TestClient(create_app(FakeEngine()))
    page = client.get("/")
    assert page.status_code == 200
    assert "Sistema de asistencia" in page.text
    payload = client.get("/api/status").json()
    assert payload["state"] == "no_gallery"
    assert payload["hands"] == 0
    assert payload["gesture_number"] is None
    assert payload["next_step"] == NEXT_STEP_PLACEHOLDER
    assert "gesture" in page.text
    assert "Iniciar prueba" in page.text
    assert "kiosk.js?v=" in page.text
    assert client.get("/api/photo/bad.id").status_code == 400
    assert client.get("/api/photo/99999999").status_code == 404
    gallery = client.get("/api/web-gallery")
    assert gallery.status_code == 200
    assert "students" in gallery.json()
    start = client.post("/api/challenge/start")
    assert start.status_code == 400
    reset = client.post("/api/challenge/reset")
    assert reset.status_code == 200
    assert reset.json()["ok"] is True
