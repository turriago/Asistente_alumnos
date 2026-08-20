"""Detección de manos con MediaPipe."""

from attendance_system.hands.detector import (
    HandDetector,
    HandDetectorError,
    apply_mirror_handedness,
    parse_hand_result,
)
from attendance_system.hands.fingers import FingerReading, NumberSmoother, count_extended_fingers, read_number
from attendance_system.hands.focus import select_gesture_hands
from attendance_system.hands.model import HandsModelError
from attendance_system.hands.types import HAND_CONNECTIONS, DetectedHand

__all__ = [
    "HAND_CONNECTIONS",
    "DetectedHand",
    "FingerReading",
    "HandDetector",
    "HandDetectorError",
    "HandsModelError",
    "NumberSmoother",
    "apply_mirror_handedness",
    "count_extended_fingers",
    "parse_hand_result",
    "read_number",
    "select_gesture_hands",
]
