"""Reto de 3 números aleatorios seguidos. Una foto fija no puede cambiar el gesto."""

from __future__ import annotations

import random
from dataclasses import dataclass

from attendance_system.config import ChallengeSettings

GRACE_SECONDS = 1.5
SUCCESS_MESSAGE = "Su prueba fue exitosa."


@dataclass(frozen=True)
class ChallengeView:
    state: str
    student_id: str | None
    sequence: tuple[int, ...]
    index: int
    target: int | None
    accepted: tuple[int, ...]
    remaining_seconds: float
    waiting_release: bool
    message: str
    frozen: bool = False

    @property
    def step(self) -> int:
        return min(self.index + 1, max(1, len(self.sequence)))

    @property
    def total(self) -> int:
        return len(self.sequence)


class ChallengeManager:
    """La prueba empieza con el botón. Al completar, se congela hasta reiniciar."""

    def __init__(
        self,
        settings: ChallengeSettings,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.settings = settings
        self._rng = rng or random.Random()
        self._phase = "idle"
        self._student_id: str | None = None
        self._sequence: tuple[int, ...] = ()
        self._index = 0
        self._accepted: list[int] = []
        self._deadline = 0.0
        self._waiting_release = False
        self._last_accepted: int | None = None
        self._last_seen = 0.0
        self._cooldown_until = 0.0

    def make_sequence(self) -> tuple[int, ...]:
        numbers: list[int] = []
        low = self.settings.min_number
        high = self.settings.max_number
        length = self.settings.sequence_length
        for _ in range(length):
            choices = [n for n in range(low, high + 1) if not numbers or n != numbers[-1]]
            if not choices:
                choices = list(range(low, high + 1))
            numbers.append(self._rng.choice(choices))
        return tuple(numbers)

    def request_start(self, *, now: float, student_id: str) -> bool:
        if self._phase in {"challenge", "success"}:
            return False
        if not student_id:
            return False
        self._start(student_id, now)
        return True

    def reset(self) -> None:
        self._phase = "idle"
        self._clear()
        self._cooldown_until = 0.0

    @property
    def idle(self) -> bool:
        return self._phase == "idle"

    def observe(
        self,
        *,
        now: float,
        student_id: str | None,
        identified: bool,
        gesture_number: int | None,
    ) -> ChallengeView:
        present = student_id if identified and student_id else None
        if present:
            self._last_seen = now

        if self._phase == "success":
            return self._view(now)

        if self._phase == "failed":
            if now < self._cooldown_until:
                return self._view(now)
            self.reset()
            return self._view(now)

        if self._phase == "idle":
            return self._view(now)

        if present and present != self._student_id:
            self.reset()
            return self._view(now)
        if present is None and now - self._last_seen > GRACE_SECONDS:
            self.reset()
            return self._view(now)

        return self._tick(now, gesture_number)

    def _start(self, student_id: str, now: float) -> None:
        self._phase = "challenge"
        self._student_id = student_id
        self._sequence = self.make_sequence()
        self._index = 0
        self._accepted = []
        self._waiting_release = False
        self._last_accepted = None
        self._deadline = now + self.settings.timeout_seconds
        self._last_seen = now

    def _clear(self) -> None:
        self._student_id = None
        self._sequence = ()
        self._index = 0
        self._accepted = []
        self._waiting_release = False
        self._last_accepted = None
        self._deadline = 0.0

    def _fail(self, now: float) -> None:
        self._phase = "failed"
        self._cooldown_until = now + self.settings.cooldown_seconds
        self._waiting_release = False

    def _succeed(self, now: float) -> None:
        self._phase = "success"
        self._waiting_release = False

    def _tick(self, now: float, gesture_number: int | None) -> ChallengeView:
        if now > self._deadline:
            self._fail(now)
            return self._view(now)

        if self._waiting_release:
            if gesture_number is None or gesture_number != self._last_accepted:
                self._waiting_release = False
                self._deadline = now + self.settings.timeout_seconds
            else:
                return self._view(now)

        target = self._sequence[self._index] if self._index < len(self._sequence) else None
        if target is not None and gesture_number == target:
            self._accepted.append(target)
            self._last_accepted = target
            self._index += 1
            if self._index >= len(self._sequence):
                self._succeed(now)
            else:
                self._waiting_release = True
                self._deadline = now + self.settings.timeout_seconds
        return self._view(now)

    def _view(self, now: float) -> ChallengeView:
        remaining = 0.0
        target: int | None = None
        if self._phase == "challenge":
            remaining = max(0.0, self._deadline - now)
            if not self._waiting_release and self._index < len(self._sequence):
                target = self._sequence[self._index]
        return ChallengeView(
            state=self._phase,
            student_id=self._student_id,
            sequence=self._sequence,
            index=self._index,
            target=target,
            accepted=tuple(self._accepted),
            remaining_seconds=round(remaining, 1),
            waiting_release=self._waiting_release,
            message=self._message(remaining, target),
            frozen=self._phase == "success",
        )

    def _message(self, remaining: float, target: int | None) -> str:
        total = len(self._sequence) or self.settings.sequence_length
        if self._phase == "idle":
            return "Pulsa Iniciar prueba cuando te reconozca."
        if self._phase == "success":
            return SUCCESS_MESSAGE
        if self._phase == "failed":
            return "Tiempo agotado. Espera un momento y pulsa Iniciar prueba otra vez."
        if self._waiting_release:
            done = self._index
            return f"Bien ({done}/{total}). Baja las manos para el siguiente número."
        if target is None:
            return "Prepara las manos."
        seconds = max(1, int(remaining))
        return (
            f"Muestra {target} con los dedos ({self._index + 1}/{total}). "
            f"Te quedan {seconds}s. Una foto no sirve: hay que cambiar el gesto."
        )
