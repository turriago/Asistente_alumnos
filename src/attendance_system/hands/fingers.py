"""Recuento de dedos 1–10. Sin desafío aleatorio ni asistencia."""

from __future__ import annotations

import math
from dataclasses import dataclass

from attendance_system.hands.types import DetectedHand

WRIST = 0
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
PINKY_MCP = 17
# (tip, pip, mcp) índice, medio, anular, meñique
_OTHER_FINGERS: tuple[tuple[int, int, int], ...] = (
    (8, 6, 5),
    (12, 10, 9),
    (16, 14, 13),
    (20, 18, 17),
)
# Dedo estirado: casi alineado y la punta lejos del nudillo (un puño de frente no cuenta).
MIN_FINGER_ALIGN = 0.62
MIN_FINGER_SPAN = 1.85


@dataclass(frozen=True)
class FingerReading:
    per_hand: tuple[int, ...]
    total: int
    number: int | None


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _dot(point: tuple[int, int], end: tuple[int, int], origin: tuple[int, int]) -> float:
    return (point[0] - origin[0]) * (end[0] - origin[0]) + (point[1] - origin[1]) * (end[1] - origin[1])


def _align(start: tuple[int, int], mid: tuple[int, int], end: tuple[int, int]) -> float:
    ax, ay = mid[0] - start[0], mid[1] - start[1]
    bx, by = end[0] - mid[0], end[1] - mid[1]
    na = math.hypot(ax, ay)
    nb = math.hypot(bx, by)
    if na < 1 or nb < 1:
        return 0.0
    return (ax * bx + ay * by) / (na * nb)


def _beyond_joint(
    points: tuple[tuple[int, int], ...],
    tip_index: int,
    joint_index: int,
    origin_index: int,
    ratio: float,
) -> bool:
    origin = points[origin_index]
    joint = points[joint_index]
    tip = points[tip_index]
    length2 = _dist(joint, origin) ** 2
    if length2 < 1:
        return False
    return _dot(tip, joint, origin) > length2 * ratio


def _dist3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _align3(
    start: tuple[float, float, float],
    mid: tuple[float, float, float],
    end: tuple[float, float, float],
) -> float:
    ax, ay, az = mid[0] - start[0], mid[1] - start[1], mid[2] - start[2]
    bx, by, bz = end[0] - mid[0], end[1] - mid[1], end[2] - mid[2]
    na = math.sqrt(ax * ax + ay * ay + az * az)
    nb = math.sqrt(bx * bx + by * by + bz * bz)
    if na < 1e-8 or nb < 1e-8:
        return 0.0
    return (ax * bx + ay * by + az * bz) / (na * nb)


def _finger_extended_3d(
    world: tuple[tuple[float, float, float], ...],
    tip_index: int,
    pip_index: int,
    mcp_index: int,
) -> bool:
    mcp = world[mcp_index]
    pip = world[pip_index]
    tip = world[tip_index]
    bone = _dist3(mcp, pip)
    if bone < 1e-6:
        return False
    span = _dist3(mcp, tip)
    if span < bone * 1.80:
        return False
    if _align3(mcp, pip, tip) < 0.55:
        return False
    return True


def _finger_fully_extended(
    points: tuple[tuple[int, int], ...],
    tip_index: int,
    pip_index: int,
    mcp_index: int,
    ratio: float,
    *,
    min_align: float = MIN_FINGER_ALIGN,
    min_span: float = MIN_FINGER_SPAN,
) -> bool:
    if not _beyond_joint(points, tip_index, pip_index, mcp_index, ratio):
        return False
    mcp = points[mcp_index]
    pip = points[pip_index]
    tip = points[tip_index]
    bone = _dist(mcp, pip)
    if bone < 1:
        return False
    if _dist(mcp, tip) < bone * min_span:
        return False
    if _align(mcp, pip, tip) < min_align:
        return False
    return True


def _thumb_away_from_palm(points: tuple[tuple[int, int], ...]) -> bool:
    """Pulgar abierto: separado de la palma, no cruzado sobre ella."""
    tip = points[THUMB_TIP]
    ip = points[THUMB_IP]
    mcp = points[THUMB_MCP]
    index_mcp = points[INDEX_MCP]
    pinky_mcp = points[PINKY_MCP]
    palm = _dist(index_mcp, pinky_mcp)
    if palm < 1:
        return False
    if _dist(tip, pinky_mcp) <= _dist(mcp, pinky_mcp) * 1.02:
        return False
    if _dist(tip, pinky_mcp) < palm * 0.52:
        return False
    if _dist(tip, index_mcp) < palm * 0.32:
        return False
    palm_center = (
        (points[WRIST][0] + index_mcp[0] + pinky_mcp[0]) / 3.0,
        (points[WRIST][1] + index_mcp[1] + pinky_mcp[1]) / 3.0,
    )
    if _dist(tip, palm_center) < _dist(ip, palm_center):
        return False
    return True


def _thumb_extended(
    points: tuple[tuple[int, int], ...],
    world: tuple[tuple[float, float, float], ...],
    *,
    thumb_ratio: float,
    other_fingers: int,
) -> bool:
    if not _thumb_away_from_palm(points):
        return False
    # Palma abierta: el pulgar sale de lado; no hace falta que esté recto.
    if other_fingers >= 4:
        return True
    if len(world) >= 21:
        return _finger_extended_3d(world, THUMB_TIP, THUMB_IP, THUMB_MCP)
    return _finger_fully_extended(
        points,
        THUMB_TIP,
        THUMB_IP,
        THUMB_MCP,
        thumb_ratio,
        min_align=0.28,
        min_span=1.25,
    )


def count_extended_fingers(
    hand: DetectedHand,
    *,
    finger_ratio: float = 1.08,
    thumb_ratio: float = 1.12,
) -> int:
    points = hand.landmarks
    if len(points) < 21:
        return 0
    world = hand.world
    raised = 0
    for tip_index, pip_index, mcp_index in _OTHER_FINGERS:
        if len(world) >= 21:
            open_finger = _finger_extended_3d(
                world, tip_index, pip_index, mcp_index
            ) and _finger_fully_extended(
                points, tip_index, pip_index, mcp_index, finger_ratio
            )
        else:
            open_finger = _finger_fully_extended(
                points, tip_index, pip_index, mcp_index, finger_ratio
            )
        if open_finger:
            raised += 1
    if _thumb_extended(
        points, world, thumb_ratio=thumb_ratio, other_fingers=raised
    ):
        raised += 1
    return min(5, raised)


def read_number(
    hands: list[DetectedHand],
    *,
    finger_ratio: float = 1.08,
    thumb_ratio: float = 1.12,
) -> FingerReading:
    if not hands:
        return FingerReading(per_hand=(), total=0, number=None)
    chosen = min(hands, key=lambda hand: hand.landmarks[0][1] if hand.landmarks else 10_000)
    count = count_extended_fingers(chosen, finger_ratio=finger_ratio, thumb_ratio=thumb_ratio)
    number = count if 1 <= count <= 5 else None
    return FingerReading(per_hand=(count,), total=count, number=number)


class NumberSmoother:
    """Evita que el dígito parpadee entre frames."""

    def __init__(self, stable_ms: int) -> None:
        self.stable_ms = max(0, stable_ms)
        self._candidate: int | None = None
        self._candidate_since = 0.0
        self.value: int | None = None

    def update(self, number: int | None, now: float) -> int | None:
        if number == self.value:
            self._candidate = number
            self._candidate_since = now
            return self.value
        if number != self._candidate:
            self._candidate = number
            self._candidate_since = now
            if self.stable_ms == 0:
                self.value = number
            return self.value
        if (now - self._candidate_since) * 1000.0 >= self.stable_ms:
            self.value = number
        return self.value

    def reset(self) -> None:
        self._candidate = None
        self._candidate_since = 0.0
        self.value = None
