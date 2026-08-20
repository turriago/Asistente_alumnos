"""Calidad del frame: oscuridad, IR vs RGB, realce para ver algo en pantalla."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FrameQuality:
    brightness: float
    colorfulness: float
    dark: bool


def brightness(frame: np.ndarray) -> float:
    return float(frame.mean())


def colorfulness(frame: np.ndarray) -> float:
    """Los canales RGB de una webcam de color se diferencian; una cámara IR casi no."""
    split = cv2.split(frame)
    if len(split) < 3:
        return 0.0
    blue, green, red = (channel.astype(np.int16) for channel in split[:3])
    return float(np.mean(np.abs(blue - green)) + np.mean(np.abs(green - red)))


def is_dark_frame(frame: np.ndarray, threshold: float) -> bool:
    return brightness(frame) < threshold


def assess_frame(frame: np.ndarray, dark_threshold: float) -> FrameQuality:
    bright = brightness(frame)
    return FrameQuality(
        brightness=bright,
        colorfulness=colorfulness(frame),
        dark=bright < dark_threshold,
    )


def preview_score(frame: np.ndarray) -> float:
    """Mayor = más probable que sea la webcam RGB del salón."""
    return brightness(frame) + (2.0 * colorfulness(frame))


def selection_score(frame: np.ndarray, dark_threshold: float) -> float:
    """Prioriza un frame claramente iluminado sobre uno oscuro con algo de color."""
    bright = brightness(frame)
    score = preview_score(frame)
    if bright >= dark_threshold + 20:
        return score + 1000.0
    return score


def enhance_if_dark(frame: np.ndarray, threshold: float) -> np.ndarray:
    """Estira contraste si el frame está negro. No inventa una cara que no está."""
    if not is_dark_frame(frame, threshold):
        return frame
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    luma, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = cv2.merge((clahe.apply(luma), a_ch, b_ch))
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def maybe_mirror(frame: np.ndarray, enabled: bool) -> np.ndarray:
    if not enabled:
        return frame
    return cv2.flip(frame, 1)
