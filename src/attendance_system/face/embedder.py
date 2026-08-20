"""Extracción de embeddings con OpenCV SFace."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from attendance_system.face.model import FaceModelError, ensure_sface_model
from attendance_system.face.types import DetectedFace
from attendance_system.logging_setup import get_logger

logger = get_logger("face.embedder")

MODEL_NAME = "sface_2021dec"


class EmbedderError(Exception):
    """No se pudo calcular el embedding."""


def l2_normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        raise EmbedderError("Embedding inválido (norma cero).")
    return vector / norm


def yunet_row(face: DetectedFace) -> np.ndarray:
    values: list[float] = [face.x, face.y, face.width, face.height]
    for point_x, point_y in face.landmarks:
        values.extend([point_x, point_y])
    values.append(face.score)
    return np.asarray(values, dtype=np.float32)


class FaceEmbedder:
    """SFace vía OpenCV (Apache-2.0). InsightFace no compiló en este Windows sin MSVC."""

    def __init__(self, models_root: Path) -> None:
        try:
            model_path = ensure_sface_model(models_root, auto_download=True)
            recognizer = cv2.FaceRecognizerSF.create(str(model_path), "")
        except cv2.error as exc:
            raise EmbedderError(f"OpenCV no pudo cargar SFace: {exc}") from exc
        except FaceModelError as exc:
            raise EmbedderError(str(exc)) from exc
        if recognizer is None:
            raise EmbedderError("OpenCV devolvió un reconocedor nulo.")
        self._recognizer = recognizer
        self.model_name = MODEL_NAME
        logger.info("Embedder SFace listo. Modelo=%s", MODEL_NAME)

    def embed(self, frame: np.ndarray, face: DetectedFace | None = None) -> np.ndarray:
        if face is None:
            raise EmbedderError("SFace necesita la caja de YuNet para alinear el rostro.")
        try:
            aligned = self._recognizer.alignCrop(frame, yunet_row(face))
            feature = self._recognizer.feature(aligned)
        except cv2.error as exc:
            raise EmbedderError(f"No se pudo extraer embedding: {exc}") from exc
        vector = np.asarray(feature, dtype=np.float32).reshape(-1)
        if vector.size == 0:
            raise EmbedderError("SFace devolvió un embedding vacío.")
        return l2_normalize(vector)
