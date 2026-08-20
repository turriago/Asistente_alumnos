"""Detección facial con YuNet."""

from attendance_system.face.detector import FaceDetector, FaceDetectorError, parse_yunet_faces
from attendance_system.face.model import FaceModelError
from attendance_system.face.types import DetectedFace

__all__ = [
    "DetectedFace",
    "FaceDetector",
    "FaceDetectorError",
    "FaceModelError",
    "parse_yunet_faces",
]
