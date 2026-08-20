"""Detección de rostros con OpenCV YuNet. No identifica personas."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from attendance_system.config import FaceSettings
from attendance_system.face.model import FaceModelError, ensure_yunet_model
from attendance_system.face.types import DetectedFace
from attendance_system.logging_setup import get_logger

logger = get_logger("face.detector")

# YuNet: x, y, w, h, 5 landmarks (x,y), score.
YUNET_ROW_SIZE = 15
# YuNet falla en fotos de celular 4K/5K; se reduce y se reescalan las cajas.
YUNET_MAX_SIDE = 1600


class FaceDetectorError(Exception):
    """No se pudo crear o usar el detector."""


def parse_yunet_faces(
    raw: np.ndarray | None,
    *,
    score_threshold: float,
    min_face_size: int,
) -> list[DetectedFace]:
    """Convierte la matriz de OpenCV en detecciones filtradas."""
    if raw is None or len(raw) == 0:
        return []

    faces: list[DetectedFace] = []
    for row in np.asarray(raw):
        values = np.asarray(row, dtype=np.float32).reshape(-1)
        if values.size < YUNET_ROW_SIZE:
            continue
        score = float(values[14])
        if score < score_threshold:
            continue
        width = int(round(values[2]))
        height = int(round(values[3]))
        if width < min_face_size or height < min_face_size:
            continue
        x = max(0, int(round(values[0])))
        y = max(0, int(round(values[1])))
        landmarks = tuple(
            (int(round(values[i])), int(round(values[i + 1])))
            for i in range(4, 14, 2)
        )
        faces.append(
            DetectedFace(
                x=x,
                y=y,
                width=width,
                height=height,
                score=score,
                landmarks=landmarks,
            )
        )
    faces.sort(key=lambda face: face.area, reverse=True)
    return faces


def resize_for_yunet(
    frame: np.ndarray,
    *,
    max_side: int = YUNET_MAX_SIDE,
) -> tuple[np.ndarray, float]:
    height, width = frame.shape[:2]
    longest = max(height, width)
    if longest <= max_side:
        return frame, 1.0
    scale = max_side / longest
    resized = cv2.resize(
        frame,
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )
    return resized, scale


def scale_faces(faces: list[DetectedFace], scale: float) -> list[DetectedFace]:
    if scale == 1.0 or not faces:
        return faces
    inverse = 1.0 / scale
    mapped: list[DetectedFace] = []
    for face in faces:
        mapped.append(
            DetectedFace(
                x=int(round(face.x * inverse)),
                y=int(round(face.y * inverse)),
                width=int(round(face.width * inverse)),
                height=int(round(face.height * inverse)),
                score=face.score,
                landmarks=tuple(
                    (int(round(x * inverse)), int(round(y * inverse)))
                    for x, y in face.landmarks
                ),
            )
        )
    return mapped


class FaceDetector:
    """Detector YuNet sobre CPU. Un frame → lista de cajas, sin nombres."""

    def __init__(self, settings: FaceSettings) -> None:
        if settings.detector != "yunet":
            raise FaceDetectorError(
                f"Detector no soportado en esta fase: {settings.detector}. Usa 'yunet'."
            )
        model_path = ensure_yunet_model(settings.model_path, auto_download=settings.auto_download)
        try:
            detector = cv2.FaceDetectorYN.create(
                str(model_path),
                "",
                (320, 320),
                float(settings.score_threshold),
                float(settings.nms_threshold),
                5000,
            )
        except cv2.error as exc:
            raise FaceDetectorError(f"OpenCV no pudo cargar YuNet: {exc}") from exc
        if detector is None:
            raise FaceDetectorError("OpenCV devolvió un detector nulo.")
        self.settings = settings
        self._detector = detector
        self._input_size: tuple[int, int] | None = None
        logger.info("Detector facial YuNet listo. Modelo: %s", model_path)

    def detect(self, frame: np.ndarray[Any, np.dtype[np.uint8]]) -> list[DetectedFace]:
        if frame is None or frame.size == 0:
            return []
        work, scale = resize_for_yunet(frame)
        work_h, work_w = work.shape[:2]
        size = (work_w, work_h)
        if self._input_size != size:
            self._detector.setInputSize(size)
            self._input_size = size
        try:
            _retval, raw = self._detector.detect(work)
        except cv2.error as exc:
            logger.error("Error de detección facial: %s", exc)
            return []
        faces = parse_yunet_faces(
            raw,
            score_threshold=self.settings.score_threshold,
            min_face_size=self.settings.min_face_size,
        )
        return scale_faces(faces, scale)
