from __future__ import annotations

import random

from attendance_system.challenge.manager import ChallengeManager
from attendance_system.config import ChallengeSettings


def _settings(**overrides: object) -> ChallengeSettings:
    values: dict[str, object] = {
        "sequence_length": 3,
        "timeout_seconds": 10.0,
        "cooldown_seconds": 4.0,
        "min_number": 1,
        "max_number": 5,
    }
    values.update(overrides)
    return ChallengeSettings(**values)  # type: ignore[arg-type]


def test_sequence_is_three_consecutive_one_hand() -> None:
    manager = ChallengeManager(_settings(), rng=random.Random(0))
    for _ in range(40):
        sequence = manager.make_sequence()
        assert len(sequence) == 3
        assert all(1 <= n <= 5 for n in sequence)
        assert sequence[1] == sequence[0] + 1
        assert sequence[2] == sequence[1] + 1


def test_stays_idle_until_button_start() -> None:
    manager = ChallengeManager(_settings(), rng=random.Random(1))
    view = manager.observe(now=0.0, student_id="TMP-0001", identified=True, gesture_number=None)
    assert view.state == "idle"
    assert view.target is None
    assert manager.request_start(now=0.0, student_id="TMP-0001") is True


def test_three_numbers_with_release_pass() -> None:
    manager = ChallengeManager(_settings(), rng=random.Random(1))
    assert manager.request_start(now=0.0, student_id="TMP-0001") is True
    view = manager.observe(now=0.0, student_id="TMP-0001", identified=True, gesture_number=None)
    assert view.state == "challenge"
    assert view.target is not None
    first = view.target
    view = manager.observe(now=0.5, student_id="TMP-0001", identified=True, gesture_number=first)
    assert view.waiting_release is True
    assert view.target is None
    view = manager.observe(now=0.8, student_id="TMP-0001", identified=True, gesture_number=None)
    second = view.target
    assert second is not None and second != first
    view = manager.observe(now=1.0, student_id="TMP-0001", identified=True, gesture_number=second)
    view = manager.observe(now=1.2, student_id="TMP-0001", identified=True, gesture_number=None)
    third = view.target
    assert third is not None and third != second
    view = manager.observe(now=1.4, student_id="TMP-0001", identified=True, gesture_number=third)
    assert view.state == "success"
    assert view.frozen is True
    assert view.message == "Su prueba fue exitosa."
    assert view.accepted == (first, second, third)
    later = manager.observe(now=20.0, student_id=None, identified=False, gesture_number=None)
    assert later.state == "success"
    assert later.frozen is True


def test_same_photo_number_does_not_skip_ahead() -> None:
    manager = ChallengeManager(_settings(), rng=random.Random(2))
    manager.request_start(now=0.0, student_id="A")
    view = manager.observe(now=0.0, student_id="A", identified=True, gesture_number=None)
    first = view.target
    assert first is not None
    view = manager.observe(now=0.4, student_id="A", identified=True, gesture_number=first)
    assert view.waiting_release is True
    still = manager.observe(now=1.0, student_id="A", identified=True, gesture_number=first)
    assert still.waiting_release is True
    assert still.index == 1
    assert still.state == "challenge"


def test_timeout_fails() -> None:
    manager = ChallengeManager(_settings(timeout_seconds=2.0), rng=random.Random(3))
    manager.request_start(now=0.0, student_id="A")
    manager.observe(now=0.0, student_id="A", identified=True, gesture_number=None)
    view = manager.observe(now=2.1, student_id="A", identified=True, gesture_number=None)
    assert view.state == "failed"


def test_does_not_reveal_upcoming_numbers() -> None:
    manager = ChallengeManager(_settings(), rng=random.Random(4))
    manager.request_start(now=0.0, student_id="A")
    view = manager.observe(now=0.0, student_id="A", identified=True, gesture_number=None)
    assert view.target == view.sequence[0]
    for later in view.sequence[1:]:
        if later != view.target:
            assert f"Muestra {later}" not in view.message
