"""Detección de manos con MediaPipe Tasks. No interpreta números 1–10."""

from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np

from attendance_system.config import HandsSettings
from attendance_system.hands.model import ensure_hand_landmarker
from attendance_system.hands.types import DetectedHand
from attendance_system.logging_setup import get_logger

logger = get_logger("hands.detector")


class HandDetectorError(Exception):
    """No se pudo crear o usar el detector de manos."""


def _xyz(landmark: Any) -> tuple[float, float, float]:
    return (
        float(getattr(landmark, "x", 0.0) or 0.0),
        float(getattr(landmark, "y", 0.0) or 0.0),
        float(getattr(landmark, "z", 0.0) or 0.0),
    )


def _world_points(landmarks: Any, world_landmarks: Any, width: int, height: int) -> tuple[tuple[float, float, float], ...]:
    if world_landmarks:
        return tuple(_xyz(item) for item in world_landmarks)
    zs = [float(getattr(item, "z", 0.0) or 0.0) for item in landmarks]
    if not zs or max(zs) - min(zs) < 1e-4:
        return ()
    return tuple(
        (float(item.x) * width, float(item.y) * height, float(getattr(item, "z", 0.0) or 0.0) * width)
        for item in landmarks
    )


def parse_hand_result(result: Any, width: int, height: int) -> list[DetectedHand]:
    """Convierte el resultado de MediaPipe en puntos de píxel y, si hay, 3D."""
    if result is None:
        return []
    landmarks_list = getattr(result, "hand_landmarks", None) or []
    handedness_list = getattr(result, "handedness", None) or []
    world_list = getattr(result, "hand_world_landmarks", None) or []
    hands: list[DetectedHand] = []
    for index, landmarks in enumerate(landmarks_list):
        points: list[tuple[int, int]] = []
        for landmark in landmarks:
            x = int(round(float(landmark.x) * width))
            y = int(round(float(landmark.y) * height))
            points.append((x, y))
        label = "Unknown"
        score = 0.0
        if index < len(handedness_list) and handedness_list[index]:
            category = handedness_list[index][0]
            label = str(
                getattr(category, "category_name", None)
                or getattr(category, "display_name", None)
                or "Unknown"
            )
            score = float(getattr(category, "score", 0.0) or 0.0)
        world_raw = world_list[index] if index < len(world_list) else None
        hands.append(
            DetectedHand(
                landmarks=tuple(points),
                handedness=label,
                score=score,
                world=_world_points(landmarks, world_raw, width, height),
            )
        )
    return hands


def apply_mirror_handedness(hands: list[DetectedHand], *, mirrored: bool) -> list[DetectedHand]:
    if not mirrored:
        return hands
    return [hand.swapped_handedness() for hand in hands]


class HandDetector:
    """Hand Landmarker en modo VIDEO. Un frame → esqueletos, sin gestos."""

    def __init__(self, settings: HandsSettings) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
        except ImportError as exc:
            raise HandDetectorError(
                "Falta MediaPipe. En el venv ejecuta: pip install -e \".[dev]\""
            ) from exc

        model_path = ensure_hand_landmarker(settings.model_path, auto_download=settings.auto_download)
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=settings.max_num_hands,
            min_hand_detection_confidence=settings.min_detection_confidence,
            min_hand_presence_confidence=settings.min_presence_confidence,
            min_tracking_confidence=settings.min_tracking_confidence,
        )
        try:
            landmarker = vision.HandLandmarker.create_from_options(options)
        except Exception as exc:
            raise HandDetectorError(f"MediaPipe no pudo cargar las manos: {exc}") from exc
        self.settings = settings
        self._mp = mp
        self._landmarker = landmarker
        self._started = time.monotonic()
        self._timestamp_ms = 0
        logger.info("Detector de manos listo. Modelo: %s", model_path)

    def detect(self, frame: np.ndarray, *, mirrored: bool = False) -> list[DetectedHand]:
        if frame is None or frame.size == 0:
            return []
        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        now_ms = int((time.monotonic() - self._started) * 1000)
        if now_ms <= self._timestamp_ms:
            now_ms = self._timestamp_ms + 1
        self._timestamp_ms = now_ms
        try:
            result = self._landmarker.detect_for_video(image, self._timestamp_ms)
        except Exception as exc:
            logger.error("Error de detección de manos: %s", exc)
            return []
        hands = parse_hand_result(result, width, height)
        return apply_mirror_handedness(hands, mirrored=mirrored)

    def close(self) -> None:
        closer = getattr(self._landmarker, "close", None)
        if closer is not None:
            closer()
