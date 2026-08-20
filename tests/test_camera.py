from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from attendance_system.camera.capture import (
    Camera,
    CameraUnavailableError,
    FpsMeter,
)
from attendance_system.config import CameraSettings


def settings(**overrides: Any) -> CameraSettings:
    values = {
        "index": 0,
        "width": 640,
        "height": 480,
        "fps": 30,
        "backend": "dshow",
        "reconnect_attempts": 2,
        "reconnect_delay_seconds": 0.0,
        "mirror": False,
        "auto_select": False,
        "dark_mean_threshold": 45.0,
        "warmup_frames": 2,
    }
    values.update(overrides)
    return CameraSettings(**values)


class FakeCapture:
    def __init__(
        self,
        opened: bool = True,
        fail_read: bool = False,
        width: int = 640,
        height: int = 480,
    ) -> None:
        self.opened = opened
        self.fail_read = fail_read
        self.released = False
        self.width = width
        self.height = height
        self.frame = np.zeros((height, width, 3), dtype=np.uint8)

    def isOpened(self) -> bool:
        return self.opened and not self.released

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.fail_read or not self.isOpened():
            return False, None
        return True, self.frame

    def set(self, *_args: object) -> bool:
        return True

    def get(self, prop: int) -> float:
        import cv2

        mapping = {
            cv2.CAP_PROP_FRAME_WIDTH: float(self.width),
            cv2.CAP_PROP_FRAME_HEIGHT: float(self.height),
            cv2.CAP_PROP_BACKEND: 700.0,
        }
        return mapping.get(prop, 0.0)

    def release(self) -> None:
        self.released = True


def test_fps_meter_computes_rate_from_timestamps() -> None:
    meter = FpsMeter(window_seconds=1.0)
    assert meter.tick(0.0) == 0.0
    # 10 ticks spanning 1 second after the first → 10 FPS
    fps = 0.0
    for i in range(1, 11):
        fps = meter.tick(i / 10)
    assert fps == pytest.approx(10.0, abs=0.01)


def test_fps_meter_rejects_non_positive_window() -> None:
    with pytest.raises(ValueError):
        FpsMeter(window_seconds=0)


def test_open_camera_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeCapture()
    monkeypatch.setattr("attendance_system.camera.capture.cv2.VideoCapture", lambda *_: fake)

    camera = Camera(settings())
    info = camera.open()

    assert info.width == 640
    assert info.height == 480
    assert info.index == 0
    frame = camera.read()
    assert frame.shape == (480, 640, 3)
    camera.release()
    assert fake.released is True


def test_open_camera_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeCapture(opened=False)
    monkeypatch.setattr("attendance_system.camera.capture.cv2.VideoCapture", lambda *_: fake)

    camera = Camera(settings(backend="any"))
    with pytest.raises(CameraUnavailableError, match="Cámara no disponible"):
        camera.open()


def test_read_fails_when_frame_is_lost(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeCapture()
    monkeypatch.setattr("attendance_system.camera.capture.cv2.VideoCapture", lambda *_: fake)

    camera = Camera(settings())
    camera.open()
    fake.fail_read = True
    with pytest.raises(CameraUnavailableError, match="perdió el frame"):
        camera.read()


def test_reconnect_gives_up_after_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeCapture(opened=False)
    monkeypatch.setattr("attendance_system.camera.capture.cv2.VideoCapture", lambda *_: fake)

    camera = Camera(settings(backend="any", reconnect_attempts=2, reconnect_delay_seconds=0))
    with pytest.raises(CameraUnavailableError):
        camera.reconnect()
