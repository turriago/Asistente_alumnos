from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from attendance_system.drawing import draw_hands
from attendance_system.hands.detector import apply_mirror_handedness, parse_hand_result
from attendance_system.face.types import DetectedFace
from attendance_system.hands.fingers import NumberSmoother, count_extended_fingers, read_number
from attendance_system.hands.focus import select_gesture_hands
from attendance_system.hands.model import HandsModelError, ensure_hand_landmarker
from attendance_system.hands.types import DetectedHand
from attendance_system.kiosk.status import NEXT_STEP_PLACEHOLDER, next_step_message


def test_parse_hand_result_scales_and_labels() -> None:
    landmark = SimpleNamespace(x=0.25, y=0.5)
    result = SimpleNamespace(
        hand_landmarks=[[landmark, SimpleNamespace(x=0.5, y=0.5)]],
        handedness=[[SimpleNamespace(category_name="Right", score=0.91)]],
    )
    hands = parse_hand_result(result, width=200, height=100)
    assert len(hands) == 1
    assert hands[0].handedness == "Right"
    assert hands[0].score == pytest.approx(0.91)
    assert hands[0].landmarks[0] == (50, 50)
    assert hands[0].landmarks[1] == (100, 50)


def test_parse_empty_result() -> None:
    assert parse_hand_result(None, 100, 100) == []
    assert parse_hand_result(SimpleNamespace(hand_landmarks=[], handedness=[]), 100, 100) == []


def test_mirror_swaps_left_and_right() -> None:
    left = DetectedHand(landmarks=((10, 10),), handedness="Left", score=0.8)
    right = DetectedHand(landmarks=((20, 20),), handedness="Right", score=0.7)
    swapped = apply_mirror_handedness([left, right], mirrored=True)
    assert [hand.handedness for hand in swapped] == ["Right", "Left"]
    same = apply_mirror_handedness([left], mirrored=False)
    assert same[0].handedness == "Left"


def test_draw_hands_changes_pixels() -> None:
    frame = np.zeros((160, 220, 3), dtype=np.uint8)
    hand = DetectedHand(
        landmarks=tuple((12 + index * 8, 40) for index in range(21)),
        handedness="Right",
        score=0.88,
    )
    drawn = draw_hands(frame, [hand])
    assert drawn.shape == frame.shape
    assert not np.array_equal(drawn, frame)


def test_next_step_shows_number() -> None:
    assert "Una mano" in next_step_message([])
    assert next_step_message([]) == NEXT_STEP_PLACEHOLDER
    one = DetectedHand(landmarks=((1, 1),), handedness="Right", score=0.9)
    assert "Dedos" in next_step_message([one])
    assert "Número leído: 7" in next_step_message([one], gesture_number=7)
    assert "no disponibles" in next_step_message([], hands_error="sin modelo")


def test_missing_hand_model_without_download(tmp_path) -> None:
    with pytest.raises(HandsModelError, match="Hand Landmarker"):
        ensure_hand_landmarker(tmp_path / "missing.task", auto_download=False)


def _hand(
    *,
    thumb: bool,
    index: bool,
    middle: bool,
    ring: bool,
    pinky: bool,
    thumb_across: bool = False,
) -> DetectedHand:
    points = [(100, 200)] * 21
    points[0] = (100, 200)
    points[1] = (85, 190)
    points[2] = (75, 188)
    points[3] = (68, 186)
    if thumb_across:
        points[2] = (85, 165)
        points[3] = (112, 155)
        points[4] = (140, 152)
    elif thumb:
        points[4] = (28, 178)
    else:
        points[4] = (88, 156)

    def place(mcp: int, pip: int, tip: int, x: int, up: bool) -> None:
        points[mcp] = (x, 150)
        points[pip] = (x, 118)
        points[tip] = (x, 48) if up else (x, 158)

    place(5, 6, 8, 90, index)
    place(9, 10, 12, 110, middle)
    place(13, 14, 16, 128, ring)
    place(17, 18, 20, 146, pinky)
    return DetectedHand(landmarks=tuple(points), handedness="Right", score=0.95)


def test_counts_open_palm_as_five() -> None:
    hand = _hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
    assert count_extended_fingers(hand) == 5


def test_counts_fist_as_zero() -> None:
    hand = _hand(thumb=False, index=False, middle=False, ring=False, pinky=False)
    assert count_extended_fingers(hand) == 0
    assert read_number([hand]).number is None


def test_counts_index_only_as_one() -> None:
    hand = _hand(thumb=False, index=True, middle=False, ring=False, pinky=False)
    assert count_extended_fingers(hand) == 1
    assert read_number([hand]).number == 1


def test_uses_the_raised_hand_only() -> None:
    five = _hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
    two = _hand(thumb=False, index=True, middle=True, ring=False, pinky=False)
    raised = list(five.landmarks)
    raised[0] = (100, 40)
    five = DetectedHand(landmarks=tuple(raised), handedness="Right", score=0.95)
    reading = read_number([two, five])
    assert reading.total == 5
    assert reading.number == 5


def test_peace_sign_is_two_not_three() -> None:
    hand = _hand(thumb=False, index=True, middle=True, ring=False, pinky=False)
    assert count_extended_fingers(hand) == 2


def test_four_fingers_ignores_thumb_across_palm() -> None:
    hand = _hand(
        thumb=False,
        index=True,
        middle=True,
        ring=True,
        pinky=True,
        thumb_across=True,
    )
    assert count_extended_fingers(hand) == 4


def test_open_palm_counts_sideways_thumb() -> None:
    hand = _hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
    points = list(hand.landmarks)
    points[2] = (70, 175)
    points[3] = (48, 168)
    points[4] = (22, 155)
    bent = DetectedHand(landmarks=tuple(points), handedness="Right", score=0.95)
    assert count_extended_fingers(bent) == 5


def test_clasped_fist_facing_camera_is_zero() -> None:
    points = [(100, 200)] * 21
    points[0] = (100, 200)
    points[2] = (70, 155)
    points[3] = (68, 150)
    points[4] = (66, 148)
    for mcp, pip, tip, x in ((5, 6, 8, 80), (9, 10, 12, 95), (13, 14, 16, 110), (17, 18, 20, 125)):
        points[mcp] = (x, 150)
        points[pip] = (x, 138)
        points[tip] = (x, 132)
    hand = DetectedHand(landmarks=tuple(points), handedness="Right", score=0.99)
    assert count_extended_fingers(hand) == 0
    assert read_number([hand, hand]).number is None


def _world_finger(extended: bool, x: float) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    mcp = (x, 0.03, 0.0)
    pip = (x, 0.06, 0.0)
    tip = (x, 0.12, 0.0) if extended else (x, 0.045, 0.012)
    return mcp, pip, tip


def test_3d_counts_open_palm_and_ignores_folded_fist() -> None:
    open_2d = _hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
    world: list[tuple[float, float, float]] = [(0.0, 0.0, 0.0)] * 21
    world[0] = (0.0, 0.0, 0.0)
    world[2], world[3], world[4] = (-0.04, 0.02, 0.0), (-0.06, 0.03, 0.0), (-0.09, 0.035, 0.0)
    for mcp_i, pip_i, tip_i, x in ((5, 6, 8, -0.02), (9, 10, 12, 0.0), (13, 14, 16, 0.02), (17, 18, 20, 0.04)):
        world[mcp_i], world[pip_i], world[tip_i] = _world_finger(True, x)
    open_3d = DetectedHand(
        landmarks=open_2d.landmarks,
        handedness="Right",
        score=0.95,
        world=tuple(world),
    )
    assert count_extended_fingers(open_3d) == 5

    for mcp_i, pip_i, tip_i, x in ((5, 6, 8, -0.02), (9, 10, 12, 0.0), (13, 14, 16, 0.02), (17, 18, 20, 0.04)):
        world[mcp_i], world[pip_i], world[tip_i] = _world_finger(False, x)
    world[2], world[3], world[4] = (-0.02, 0.03, 0.0), (-0.02, 0.035, 0.01), (-0.015, 0.032, 0.015)
    fist_3d = DetectedHand(
        landmarks=open_2d.landmarks,
        handedness="Right",
        score=0.95,
        world=tuple(world),
    )
    assert count_extended_fingers(fist_3d) == 0


def test_parse_keeps_world_landmarks() -> None:
    lm = SimpleNamespace(x=0.25, y=0.5, z=-0.1)
    world = SimpleNamespace(x=0.01, y=0.02, z=0.03)
    result = SimpleNamespace(
        hand_landmarks=[[lm] * 2],
        handedness=[[SimpleNamespace(category_name="Left", score=0.8)]],
        hand_world_landmarks=[[world] * 2],
    )
    hands = parse_hand_result(result, width=200, height=100)
    assert hands[0].world[0] == pytest.approx((0.01, 0.02, 0.03))


def test_number_smoother_needs_stable_window() -> None:
    smoother = NumberSmoother(200)
    assert smoother.update(3, 0.0) is None
    assert smoother.update(3, 0.10) is None
    assert smoother.update(3, 0.21) == 3
    assert smoother.update(4, 0.22) == 3
    assert smoother.update(4, 0.50) == 4
    smoother.reset()
    assert smoother.value is None


def _shift(hand: DetectedHand, dx: int, dy: int) -> DetectedHand:
    return DetectedHand(
        landmarks=tuple((x + dx, y + dy) for x, y in hand.landmarks),
        handedness=hand.handedness,
        score=hand.score,
        world=hand.world,
    )


def _face() -> DetectedFace:
    return DetectedFace(x=60, y=10, width=80, height=90, score=0.9, landmarks=())


def test_keeps_only_hands_of_the_closest_face() -> None:
    near = _hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
    far = _shift(near, 420, 30)
    kept = select_gesture_hands([near, far], _face())
    assert kept == [near]


def test_without_a_face_ignores_all_hands() -> None:
    hand = _hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
    assert select_gesture_hands([hand], None) == []


def test_ignores_hand_hanging_too_low() -> None:
    hand = _shift(_hand(thumb=True, index=True, middle=True, ring=True, pinky=True), 0, 320)
    assert select_gesture_hands([hand], _face()) == []


def _scale_about_wrist(hand: DetectedHand, factor: float) -> DetectedHand:
    origin_x, origin_y = hand.landmarks[0]
    return DetectedHand(
        landmarks=tuple(
            (int(origin_x + (x - origin_x) * factor), int(origin_y + (y - origin_y) * factor))
            for x, y in hand.landmarks
        ),
        handedness=hand.handedness,
        score=hand.score,
        world=hand.world,
    )


def test_ignores_small_background_hands_near_the_face() -> None:
    background = _scale_about_wrist(
        _hand(thumb=True, index=True, middle=True, ring=True, pinky=True),
        0.28,
    )
    assert select_gesture_hands([background], _face()) == []


def test_keeps_large_hand_even_if_offset_from_face() -> None:
    close = _shift(_hand(thumb=True, index=True, middle=True, ring=True, pinky=True), -160, 20)
    far = _shift(
        _scale_about_wrist(_hand(thumb=True, index=True, middle=True, ring=True, pinky=True), 0.45),
        90,
        40,
    )
    kept = select_gesture_hands([far, close], _face())
    assert kept == [close]


def test_ignores_hands_of_a_smaller_face() -> None:
    close_face = DetectedFace(x=60, y=10, width=80, height=90, score=0.9, landmarks=())
    far_face = DetectedFace(x=420, y=40, width=36, height=40, score=0.8, landmarks=())
    mine = _hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
    other = _shift(
        _scale_about_wrist(_hand(thumb=False, index=True, middle=True, ring=False, pinky=False), 0.5),
        360,
        50,
    )
    kept = select_gesture_hands([mine, other], [close_face, far_face])
    assert kept == [mine]


def test_ignores_hand_resting_on_the_face() -> None:
    on_face = _shift(_hand(thumb=True, index=True, middle=True, ring=True, pinky=True), 0, -150)
    assert select_gesture_hands([on_face], _face()) == []


def test_ignores_edge_on_palm() -> None:
    points = list(_hand(thumb=True, index=True, middle=True, ring=True, pinky=True).landmarks)
    # Palma de canto: muñeca, índice y meñique casi alineados.
    points[0] = (100, 200)
    points[5] = (100, 160)
    points[17] = (102, 120)
    hand = DetectedHand(landmarks=tuple(points), handedness="Right", score=0.9)
    assert select_gesture_hands([hand], _face()) == []
