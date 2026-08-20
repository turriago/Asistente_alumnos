"""Descarga local de modelos ONNX. No se suben a Git."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from attendance_system.logging_setup import get_logger

logger = get_logger("face.model")

YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
YUNET_MIN_BYTES = 200_000

SFACE_FILENAME = "face_recognition_sface_2021dec.onnx"
SFACE_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_recognition_sface/face_recognition_sface_2021dec.onnx"
)
SFACE_MIN_BYTES = 1_000_000


class FaceModelError(Exception):
    """El modelo no está disponible o es inválido."""


def _download_onnx(url: str, path: Path, min_bytes: int, label: str) -> Path:
    if path.exists() and path.stat().st_size >= min_bytes:
        return path
    if path.exists() and path.stat().st_size < min_bytes:
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Descargando %s desde OpenCV Zoo...", label)
    tmp_path = path.with_suffix(path.suffix + ".part")
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "attendance-system-academic-demo"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
        if len(data) < min_bytes:
            raise FaceModelError(f"La descarga de {label} está incompleta.")
        tmp_path.write_bytes(data)
        tmp_path.replace(path)
    except FaceModelError:
        raise
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink()
        raise FaceModelError(
            f"No se pudo descargar {label}. Revisa internet o descarga manual: {url}"
        ) from exc
    logger.info("%s guardado en %s (%s bytes).", label, path, path.stat().st_size)
    return path


def ensure_yunet_model(path: Path, *, auto_download: bool) -> Path:
    if path.exists() and path.stat().st_size >= YUNET_MIN_BYTES:
        return path
    if not auto_download:
        raise FaceModelError(
            f"No se encontró YuNet en {path}. Ejecuta: python scripts/download_models.py"
        )
    return _download_onnx(YUNET_URL, path, YUNET_MIN_BYTES, "YuNet")


def ensure_sface_model(models_dir: Path, *, auto_download: bool) -> Path:
    path = models_dir / SFACE_FILENAME
    if path.exists() and path.stat().st_size >= SFACE_MIN_BYTES:
        return path
    if not auto_download:
        raise FaceModelError(
            f"No se encontró SFace en {path}. Ejecuta: python scripts/download_models.py"
        )
    return _download_onnx(SFACE_URL, path, SFACE_MIN_BYTES, "SFace")
