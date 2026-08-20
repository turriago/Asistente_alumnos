"""Captura de webcam del PC."""

from attendance_system.camera.capture import (
    Camera,
    CameraInfo,
    CameraUnavailableError,
    FpsMeter,
    probe_cameras,
)

__all__ = [
    "Camera",
    "CameraInfo",
    "CameraUnavailableError",
    "FpsMeter",
    "probe_cameras",
]
