"""Descarga local del modelo Hand Landmarker. No se sube a Git."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from attendance_system.logging_setup import get_logger

logger = get_logger("hands.model")

HAND_LANDMARKER_FILENAME = "hand_landmarker.task"
HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
HAND_LANDMARKER_MIN_BYTES = 1_000_000


class HandsModelError(Exception):
    """El modelo de manos no está disponible o es inválido."""


def ensure_hand_landmarker(path: Path, *, auto_download: bool) -> Path:
    if path.exists() and path.stat().st_size >= HAND_LANDMARKER_MIN_BYTES:
        return path
    if path.exists() and path.stat().st_size < HAND_LANDMARKER_MIN_BYTES:
        path.unlink()
    if not auto_download:
        raise HandsModelError(
            f"No se encontró Hand Landmarker en {path}. Ejecuta: python scripts/download_models.py"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Descargando Hand Landmarker de MediaPipe...")
    tmp_path = path.with_suffix(path.suffix + ".part")
    try:
        request = urllib.request.Request(
            HAND_LANDMARKER_URL,
            headers={"User-Agent": "attendance-system-academic-demo"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
        if len(data) < HAND_LANDMARKER_MIN_BYTES:
            raise HandsModelError("La descarga de Hand Landmarker está incompleta.")
        tmp_path.write_bytes(data)
        tmp_path.replace(path)
    except HandsModelError:
        raise
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink()
        raise HandsModelError(
            "No se pudo descargar Hand Landmarker. Revisa internet o descarga "
            f"manual: {HAND_LANDMARKER_URL}"
        ) from exc
    logger.info("Hand Landmarker guardado en %s (%s bytes).", path, path.stat().st_size)
    return path
