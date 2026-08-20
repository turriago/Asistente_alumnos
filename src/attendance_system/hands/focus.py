"""Elige solo las manos de la persona más cercana, con dedos hacia la cámara."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from attendance_system.config import HandsSettings
from attendance_system.face.types import DetectedFace
from attendance_system.hands.fingers import count_extended_fingers
from attendance_system.hands.types import DetectedHand

_FINGER_TIPS = (8, 12, 16, 20)
INDEX_MCP = 5
PINKY_MCP = 17


@dataclass(frozen=True)
class HandFocusSettings:
    max_hands: int = 2
    max_dx_faces: float = 1.65
    max_dy_below_faces: float = 2.3
    max_dy_above_faces: float = 0.85
    min_palm_to_face: float = 0.38
    min_up_fingers: int = 2
    tip_above_wrist_px: int = 10
    min_hand_of_largest: float = 0.58
    min_foreground_face: float = 0.9


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _face_center(face: DetectedFace) -> tuple[float, float]:
    return (face.x + face.width / 2, face.y + face.height / 2)


def palm_width(hand: DetectedHand) -> float:
    points = hand.landmarks
    if len(points) < 21:
        return 0.0
    return _dist(points[INDEX_MCP], points[PINKY_MCP])


def hand_extent(hand: DetectedHand) -> float:
    """Tamaño aparente: más grande = más cerca de la cámara."""
    points = hand.landmarks
    if not points:
        return 0.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return float(max(max(xs) - min(xs), max(ys) - min(ys)))


def fingers_pointing_up(hand: DetectedHand, *, min_up: int, tip_above_px: int) -> bool:
    points = hand.landmarks
    if len(points) < 21:
        return False
    wrist_y = points[0][1]
    raised = 0
    for tip in _FINGER_TIPS:
        if points[tip][1] < wrist_y - tip_above_px:
            raised += 1
    return raised >= min_up


def _point_in_face(point: tuple[int, int], face: DetectedFace, *, pad: float) -> bool:
    extra_x = face.width * pad
    extra_y = face.height * pad
    return (
        face.x - extra_x <= point[0] <= face.x + face.width + extra_x
        and face.y - extra_y <= point[1] <= face.y + face.height + extra_y
    )


def covers_face(hand: DetectedHand, face: DetectedFace) -> bool:
    """Mano en la cara, barbilla o cabeza: no es un gesto hacia la cámara."""
    points = hand.landmarks
    if len(points) < 21:
        return True
    if _point_in_face(points[0], face, pad=0.35):
        return True
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return _point_in_face((int(cx), int(cy)), face, pad=0.15)


def palm_facing_camera(hand: DetectedHand) -> bool:
    """Palma de frente. De canto o apoyada en la cabeza suele dar área pequeña."""
    points = hand.landmarks
    if len(points) < 21:
        return False
    wrist, index_mcp, pinky_mcp = points[0], points[INDEX_MCP], points[PINKY_MCP]
    area = abs(
        (index_mcp[0] - wrist[0]) * (pinky_mcp[1] - wrist[1])
        - (index_mcp[1] - wrist[1]) * (pinky_mcp[0] - wrist[0])
    ) / 2.0
    width = palm_width(hand)
    if width < 1:
        return False
    return (area / (width * width)) >= 0.28


def presented_to_camera(hand: DetectedHand, face: DetectedFace) -> bool:
    """Solo manos abiertas, de frente y fuera de la cara."""
    if covers_face(hand, face):
        return False
    if not palm_facing_camera(hand):
        return False
    wrist = hand.landmarks[0]
    if wrist[1] < face.y + face.height * 0.35:
        return False
    return True


def belongs_to_face(
    hand: DetectedHand,
    face: DetectedFace,
    *,
    settings: HandFocusSettings,
) -> bool:
    if not hand.landmarks:
        return False
    wrist = hand.landmarks[0]
    cx, cy = _face_center(face)
    width = max(face.width, 1)
    height = max(face.height, 1)
    dx = abs(wrist[0] - cx) / width
    dy = (wrist[1] - cy) / height
    if dx > settings.max_dx_faces:
        return False
    if dy < -settings.max_dy_above_faces:
        return False
    if dy > settings.max_dy_below_faces:
        return False
    if palm_width(hand) < width * settings.min_palm_to_face:
        return False
    return True


def is_foreground_hand(
    hand: DetectedHand,
    face: DetectedFace,
    *,
    settings: HandFocusSettings,
) -> bool:
    """Palma enorme frente a la cámara: es de quien está más cerca, aunque salga a un lado."""
    if hand_extent(hand) < max(face.width, 1) * settings.min_foreground_face:
        return False
    if not hand.landmarks:
        return False
    wrist = hand.landmarks[0]
    cx, cy = _face_center(face)
    width = max(face.width, 1)
    height = max(face.height, 1)
    dx = abs(wrist[0] - cx) / width
    dy = (wrist[1] - cy) / height
    if dx > settings.max_dx_faces * 2.2:
        return False
    if dy < -settings.max_dy_above_faces * 1.6:
        return False
    if dy > settings.max_dy_below_faces * 1.5:
        return False
    return True


def nearest_face(hand: DetectedHand, faces: Sequence[DetectedFace]) -> DetectedFace | None:
    if not faces or not hand.landmarks:
        return None
    wrist = hand.landmarks[0]
    return min(faces, key=lambda face: _dist(wrist, _face_center(face)))


def _as_faces(face: DetectedFace | Sequence[DetectedFace] | None) -> list[DetectedFace]:
    if face is None:
        return []
    if isinstance(face, DetectedFace):
        return [face]
    return list(face)


def select_gesture_hands(
    hands: list[DetectedHand],
    face: DetectedFace | Sequence[DetectedFace] | None,
    *,
    settings: HandFocusSettings | None = None,
) -> list[DetectedHand]:
    """Manos de la cara más grande (más cercana). Las de fondo o de paso se ignoran."""
    faces = _as_faces(face)
    if not faces or not hands:
        return []
    rules = settings or HandFocusSettings()
    primary = max(faces, key=lambda item: item.area)
    kept: list[DetectedHand] = []
    for hand in hands:
        if not presented_to_camera(hand, primary):
            continue
        if not fingers_pointing_up(
            hand,
            min_up=rules.min_up_fingers,
            tip_above_px=rules.tip_above_wrist_px,
        ):
            continue
        if count_extended_fingers(hand) < 1:
            continue
        close_to_camera = is_foreground_hand(hand, primary, settings=rules)
        owner = nearest_face(hand, faces)
        if not close_to_camera and owner is not None and owner is not primary:
            continue
        if not close_to_camera and not belongs_to_face(hand, primary, settings=rules):
            continue
        kept.append(hand)
    if not kept:
        return []
    largest = max(hand_extent(hand) for hand in kept)
    min_size = largest * rules.min_hand_of_largest
    kept = [hand for hand in kept if hand_extent(hand) >= min_size]
    kept.sort(key=hand_extent, reverse=True)
    return kept[: max(1, rules.max_hands)]


def focus_settings_from_config(hands: HandsSettings) -> HandFocusSettings:
    return HandFocusSettings(
        max_hands=2,
        max_dx_faces=hands.max_dx_faces,
        max_dy_below_faces=hands.max_dy_below_faces,
        max_dy_above_faces=hands.max_dy_above_faces,
        min_palm_to_face=hands.min_palm_to_face,
        min_up_fingers=hands.min_up_fingers,
        min_hand_of_largest=hands.min_hand_of_largest,
        min_foreground_face=hands.min_foreground_face,
    )
