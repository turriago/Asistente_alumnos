"""Dibujo de overlay y cajas. Sin lógica de reconocimiento."""

from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

from attendance_system.face.types import DetectedFace
from attendance_system.hands.types import HAND_CONNECTIONS, DetectedHand
from attendance_system.text import draw_texts, measure_text

OVERLAY_OK = (0, 255, 180)
OVERLAY_WAIT = (255, 200, 80)
OVERLAY_ERROR = (0, 0, 255)
BOX_SINGLE = (80, 220, 80)
BOX_MULTI = (0, 200, 255)
BOX_UNKNOWN = (40, 80, 255)
LANDMARK = (0, 255, 255)
HAND_LEFT = (255, 180, 80)
HAND_RIGHT = (80, 220, 255)
HAND_UNKNOWN = (200, 200, 200)
HAND_IGNORED = (90, 90, 90)


def draw_overlay(
    frame: np.ndarray,
    lines: Sequence[str],
    *,
    error: bool = False,
    waiting: bool = False,
) -> np.ndarray:
    display = frame.copy()
    if error:
        color = OVERLAY_ERROR
    elif waiting:
        color = OVERLAY_WAIT
    else:
        color = OVERLAY_OK
    items = [(line, (16, 36 + index * 36), color, 26, 2) for index, line in enumerate(lines)]
    return draw_texts(display, items)


def draw_center_warning(frame: np.ndarray, lines: Sequence[str]) -> np.ndarray:
    display = frame.copy()
    height, width = display.shape[:2]
    y = height // 2 - 40
    items: list[tuple[str, tuple[int, int], tuple[int, int, int], int, int]] = []
    for line in lines:
        text_width, _ = measure_text(line, 36)
        x = max(16, (width - text_width) // 2)
        items.append((line, (x, y), OVERLAY_ERROR, 36, 3))
        y += 42
    return draw_texts(display, items)


def draw_live_strip(frame: np.ndarray, brightness_value: float) -> np.ndarray:
    display = frame.copy()
    height, width = display.shape[:2]
    cv2.rectangle(display, (0, height - 28), (width, height), (20, 20, 20), -1)
    bar_width = int(max(4, min(width, (brightness_value / 255.0) * width)))
    cv2.rectangle(display, (0, height - 28), (bar_width, height), (0, 200, 80), -1)
    return draw_texts(
        display,
        [(f"LIVE  brillo={brightness_value:.0f}/255", (12, height - 8), (255, 255, 255), 18, 1)],
    )


def draw_faces(
    frame: np.ndarray,
    faces: Sequence[DetectedFace],
    *,
    draw_landmarks: bool = True,
    labels: Sequence[str] | None = None,
    identified: bool | None = None,
) -> np.ndarray:
    display = frame.copy()
    if identified is True:
        color = BOX_SINGLE
    elif identified is False:
        color = BOX_UNKNOWN
    else:
        color = BOX_MULTI if len(faces) > 1 else BOX_SINGLE
    texts: list[tuple[str, tuple[int, int], tuple[int, int, int], int, int]] = []
    for index, face in enumerate(faces):
        x2 = face.x + face.width
        y2 = face.y + face.height
        cv2.rectangle(display, (face.x, face.y), (x2, y2), color, 2)
        if labels is not None and index < len(labels):
            label = labels[index]
        else:
            label = f"rostro {face.score:.2f}"
        texts.append((label, (face.x, max(24, face.y - 8)), color, 20, 2))
        if draw_landmarks:
            for point in face.landmarks:
                cv2.circle(display, point, 3, LANDMARK, -1, cv2.LINE_AA)
    return draw_texts(display, texts)


def _hand_color(hand: DetectedHand) -> tuple[int, int, int]:
    name = hand.handedness.casefold()
    if name == "left":
        return HAND_LEFT
    if name == "right":
        return HAND_RIGHT
    return HAND_UNKNOWN


def draw_hands(
    frame: np.ndarray,
    hands: Sequence[DetectedHand],
    *,
    finger_counts: Sequence[int] | None = None,
    active: Sequence[bool] | None = None,
) -> np.ndarray:
    display = frame.copy()
    texts: list[tuple[str, tuple[int, int], tuple[int, int, int], int, int]] = []
    for index, hand in enumerate(hands):
        is_active = True if active is None else (index < len(active) and active[index])
        color = _hand_color(hand) if is_active else HAND_IGNORED
        thickness = 2 if is_active else 1
        radius = 4 if is_active else 2
        points = hand.landmarks
        for start, end in HAND_CONNECTIONS:
            if start >= len(points) or end >= len(points):
                continue
            cv2.line(display, points[start], points[end], color, thickness, cv2.LINE_AA)
        for point in points:
            cv2.circle(display, point, radius, color, -1, cv2.LINE_AA)
        if points:
            extra = ""
            if is_active and finger_counts is not None and index < len(finger_counts):
                extra = f"  {finger_counts[index]} dedos"
            label = f"{hand.handedness} {hand.score:.2f}{extra}"
            if not is_active:
                label = "fondo"
            texts.append((label, (points[0][0], max(24, points[0][1] - 12)), color, 18, 2))
    return draw_texts(display, texts) if texts else display


def draw_gesture_number(frame: np.ndarray, number: int | None) -> np.ndarray:
    if number is None:
        return frame
    height, width = frame.shape[:2]
    label = str(number)
    size = 72
    text_width, _ = measure_text(label, size)
    x = max(16, width - text_width - 24)
    y = min(height - 36, 88)
    return draw_texts(frame, [(label, (x, y), OVERLAY_OK, size, 3)])


def draw_challenge_prompt(
    frame: np.ndarray,
    *,
    target: int | None,
    step: int | None,
    total: int | None,
    remaining: float | None,
    waiting_release: bool = False,
    done: bool = False,
    failed: bool = False,
) -> np.ndarray:
    height, width = frame.shape[:2]
    if done:
        line = "Su prueba fue exitosa."
        color = OVERLAY_OK
    elif failed:
        line = "Reto fallido"
        color = OVERLAY_ERROR
    elif waiting_release:
        line = "Baja las manos"
        color = OVERLAY_WAIT
    elif target is None:
        return frame
    else:
        clock = f"  {max(1, int(remaining or 0))}s" if remaining is not None else ""
        progress = f"{step}/{total}" if step and total else ""
        line = f"Muestra {target}   {progress}{clock}"
        color = OVERLAY_WAIT
    size = 42
    text_width, _ = measure_text(line, size)
    x = max(16, (width - text_width) // 2)
    y = min(height - 20, 52)
    return draw_texts(frame, [(line, (x, y), color, size, 3)])
