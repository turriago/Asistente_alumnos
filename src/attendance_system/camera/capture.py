"""Acceso a la webcam local con manejo de errores y diagnóstico."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, replace
from typing import Any

import cv2
import numpy as np

from attendance_system.camera.quality import selection_score
from attendance_system.config import CameraSettings
from attendance_system.logging_setup import get_logger

logger = get_logger("camera")

BACKEND_MAP = {
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
    "any": cv2.CAP_ANY,
}


class CameraUnavailableError(Exception):
    """No se pudo abrir o leer la cámara."""


@dataclass(frozen=True)
class CameraInfo:
    index: int
    width: int
    height: int
    requested_width: int
    requested_height: int
    requested_fps: int
    backend: str
    backend_id: int


class FpsMeter:
    """FPS reales medidos sobre una ventana deslizante, no el valor pedido a OpenCV."""

    def __init__(self, window_seconds: float = 1.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds debe ser positivo.")
        self._window = window_seconds
        self._times: deque[float] = deque()

    def tick(self, now: float | None = None) -> float:
        timestamp = time.perf_counter() if now is None else now
        self._times.append(timestamp)
        cutoff = timestamp - self._window
        while self._times and self._times[0] < cutoff:
            self._times.popleft()
        if len(self._times) < 2:
            return 0.0
        elapsed = self._times[-1] - self._times[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._times) - 1) / elapsed

    def reset(self) -> None:
        self._times.clear()


def _backend_id(name: str) -> int:
    try:
        return BACKEND_MAP[name]
    except KeyError as exc:
        raise CameraUnavailableError(f"Backend de cámara no soportado: {name}") from exc


def probe_cameras(max_index: int = 5, backend: str = "dshow") -> list[int]:
    """Prueba índices 0..max_index y devuelve los que abren y entregan un frame."""
    found: list[int] = []
    backend_id = _backend_id(backend)
    for index in range(max_index + 1):
        capture = cv2.VideoCapture(index, backend_id)
        try:
            if capture.isOpened():
                ok, frame = capture.read()
                if ok and frame is not None:
                    found.append(index)
        finally:
            capture.release()
    return found


class Camera:
    """Wrapper de OpenCV VideoCapture que no deja caer el proceso por un fallo de hardware."""

    def __init__(self, settings: CameraSettings) -> None:
        self.settings = settings
        self._capture: cv2.VideoCapture | None = None

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    def open(self) -> CameraInfo:
        if self._capture is not None:
            self.release()

        backend_id = _backend_id(self.settings.backend)
        logger.info(
            "Abriendo cámara index=%s backend=%s resolución pedida=%sx%s fps pedido=%s",
            self.settings.index,
            self.settings.backend,
            self.settings.width,
            self.settings.height,
            self.settings.fps,
        )
        capture = cv2.VideoCapture(self.settings.index, backend_id)
        if not capture.isOpened() and self.settings.backend != "any":
            logger.warning(
                "No se abrió con backend=%s. Reintentando con backend any.",
                self.settings.backend,
            )
            capture.release()
            capture = cv2.VideoCapture(self.settings.index, cv2.CAP_ANY)

        if not capture.isOpened():
            capture.release()
            raise CameraUnavailableError(
                "Cámara no disponible. Revisa que esté conectada, no usada por otra "
                f"aplicación, y prueba CAMERA_INDEX distinto de {self.settings.index}."
            )

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
        capture.set(cv2.CAP_PROP_FPS, self.settings.fps)
        # DirectShow: 0.75 suele significar exposición automática.
        capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)

        last_ok = False
        last_frame = None
        warmup = max(1, self.settings.warmup_frames)
        for _ in range(warmup):
            last_ok, last_frame = capture.read()
        if not last_ok or last_frame is None:
            capture.release()
            raise CameraUnavailableError(
                "La cámara abrió pero no entregó imagen. Prueba otro índice o backend."
            )

        self._capture = capture
        info = self.info()
        logger.info(
            "Cámara iniciada. Resolución real=%sx%s backend=%s",
            info.width,
            info.height,
            info.backend,
        )
        return info

    def info(self) -> CameraInfo:
        capture = self._require_capture()
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        backend_id = int(capture.get(cv2.CAP_PROP_BACKEND) or 0)
        return CameraInfo(
            index=self.settings.index,
            width=width,
            height=height,
            requested_width=self.settings.width,
            requested_height=self.settings.height,
            requested_fps=self.settings.fps,
            backend=self.settings.backend,
            backend_id=backend_id,
        )

    def read(self) -> np.ndarray[Any, np.dtype[np.uint8]]:
        capture = self._require_capture()
        ok, frame = capture.read()
        if not ok or frame is None:
            raise CameraUnavailableError("Cámara no disponible. Se perdió el frame.")
        return frame

    def reconnect(self) -> CameraInfo:
        attempts = max(1, self.settings.reconnect_attempts)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            logger.warning("Reintentando cámara (%s/%s).", attempt, attempts)
            try:
                return self.open()
            except CameraUnavailableError as exc:
                last_error = exc
                time.sleep(self.settings.reconnect_delay_seconds)
        assert last_error is not None
        raise last_error

    def switch_index(self, index: int) -> CameraInfo:
        self.settings = replace(self.settings, index=index)
        return self.open()

    def switch_backend(self, backend: str) -> CameraInfo:
        self.settings = replace(self.settings, backend=backend)
        return self.open()

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("Cámara liberada.")

    def _require_capture(self) -> cv2.VideoCapture:
        if self._capture is None or not self._capture.isOpened():
            raise CameraUnavailableError("Cámara no disponible. No hay dispositivo abierto.")
        return self._capture

    def __enter__(self) -> Camera:
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()


@dataclass(frozen=True)
class CameraProbe:
    index: int
    backend: str
    brightness: float
    score: float


def rank_cameras(
    settings: CameraSettings,
    *,
    max_index: int = 3,
) -> list[CameraProbe]:
    """Prueba MSMF y DirectShow en varios índices. Prefiere la imagen más clara (RGB)."""
    ranked: list[CameraProbe] = []
    backends = ("msmf", "dshow")
    for backend in backends:
        backend_id = _backend_id(backend)
        for index in range(max_index + 1):
            capture = cv2.VideoCapture(index, backend_id)
            try:
                if not capture.isOpened():
                    continue
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                frame = None
                ok = False
                for _ in range(max(6, settings.warmup_frames // 2)):
                    ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                ranked.append(
                    CameraProbe(
                        index=index,
                        backend=backend,
                        brightness=float(frame.mean()),
                        score=selection_score(frame, settings.dark_mean_threshold),
                    )
                )
            finally:
                capture.release()
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def open_preferred_camera(settings: CameraSettings) -> tuple[Camera, CameraInfo]:
    """Elige la cámara RGB real. La app Cámara de Windows usa MSMF, no DirectShow."""
    if settings.auto_select:
        ranked = rank_cameras(settings)
        if ranked:
            best = ranked[0]
            logger.info(
                "Cámaras detectadas: %s. Eligiendo index=%s backend=%s (score=%.1f, brillo=%.1f).",
                [
                    (item.backend, item.index, round(item.score, 1), round(item.brightness, 1))
                    for item in ranked
                ],
                best.index,
                best.backend,
                best.score,
                best.brightness,
            )
            chosen = replace(settings, index=best.index, backend=best.backend)
            camera = Camera(chosen)
            return camera, camera.open()
        logger.warning("No se pudo inspeccionar otras cámaras. Usando la configuración.")

    camera = Camera(settings)
    return camera, camera.open()
