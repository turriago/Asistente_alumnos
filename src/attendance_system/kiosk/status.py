"""Estado visible del kiosco. Fase 8: reto de 3 números, sin registro de asistencia."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from attendance_system.challenge.manager import ChallengeView
from attendance_system.face.matcher import FaceMatcher, MatchResult
from attendance_system.face.types import DetectedFace
from attendance_system.hands.types import DetectedHand

NEXT_STEP_PLACEHOLDER = (
    "Ponte más cerca. Una mano al celular y la otra a la cámara: números del 1 al 5. "
    "Las manos de quien pasa no cuentan."
)


def next_step_message(
    hands: list[DetectedHand],
    *,
    hands_error: str | None = None,
    gesture_number: int | None = None,
    challenge: ChallengeView | None = None,
    identified: bool = False,
) -> str:
    if challenge is not None and challenge.state not in {"idle"}:
        return challenge.message
    if hands_error:
        return f"DEBUG manos: no disponibles. {hands_error}"
    if identified:
        return "Pulsa Iniciar prueba: 3 números seguidos, con una sola mano (1 a 5)."
    if gesture_number is not None:
        return f"Número leído: {gesture_number}."
    if not hands:
        return NEXT_STEP_PLACEHOLDER
    return "Dedos hacia la cámara, cerca de tu cara. Las otras personas no cuentan."


@dataclass(frozen=True)
class KioskStatus:
    state: str
    headline: str
    student_id: str | None
    full_name: str | None
    program: str | None
    group_name: str | None
    score: float | None
    threshold: float
    faces: int
    hands: int
    gesture_number: int | None
    challenge_target: int | None
    challenge_step: int | None
    challenge_total: int | None
    remaining_seconds: float | None
    fps: float
    gallery_size: int
    demo_mode: bool
    next_step: str
    photo_url: str | None
    camera_ok: bool
    can_start_test: bool = False
    scanner_paused: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _challenge_ui(challenge: ChallengeView | None) -> tuple[str | None, str | None]:
    if challenge is None or challenge.state == "idle":
        return None, None
    headlines = {
        "challenge": "Reto: muestra el número",
        "success": "Su prueba fue exitosa.",
        "failed": "Reto fallido",
        "cooldown": "Espera un momento",
        "hold": "Su prueba fue exitosa.",
    }
    state = challenge.state
    if state == "success":
        mapped = "challenge_ok"
    elif state == "failed":
        mapped = "challenge_fail"
    else:
        mapped = state
    return mapped, headlines.get(state, "Reto")


def build_status(
    *,
    faces: list[DetectedFace],
    matcher: FaceMatcher,
    result: MatchResult | None,
    fps: float,
    dark: bool,
    demo_mode: bool,
    camera_ok: bool,
    camera_error: str | None = None,
    hands: list[DetectedHand] | None = None,
    hands_error: str | None = None,
    gesture_number: int | None = None,
    challenge: ChallengeView | None = None,
) -> KioskStatus:
    detected_hands = hands or []
    identified = result is not None and result.identified
    step = next_step_message(
        detected_hands,
        hands_error=hands_error,
        gesture_number=gesture_number,
        challenge=challenge,
        identified=identified,
    )
    threshold = matcher.threshold
    challenge_target = challenge.target if challenge is not None else None
    challenge_step = None
    challenge_total = None
    remaining = None
    scanner_paused = bool(challenge is not None and challenge.frozen)
    can_start_test = (
        identified
        and camera_ok
        and not scanner_paused
        and (challenge is None or challenge.state == "idle")
    )
    if challenge is not None and challenge.sequence:
        challenge_step = min(challenge.index + 1, len(challenge.sequence))
        challenge_total = len(challenge.sequence)
        remaining = challenge.remaining_seconds

    if not camera_ok:
        return KioskStatus(
            state="camera_error",
            headline=camera_error or "Cámara no disponible",
            student_id=None,
            full_name=None,
            program=None,
            group_name=None,
            score=None,
            threshold=threshold,
            faces=0,
            hands=0,
            gesture_number=None,
            challenge_target=None,
            challenge_step=None,
            challenge_total=None,
            remaining_seconds=None,
            fps=fps,
            gallery_size=matcher.person_count,
            demo_mode=demo_mode,
            next_step=step,
            photo_url=None,
            camera_ok=False,
            can_start_test=False,
            scanner_paused=False,
        )
    if dark:
        state, headline = "dark", "Imagen oscura. Cierra la app Cámara de Windows."
    elif matcher.size == 0:
        state, headline = "no_gallery", "No hay rostros enrolados."
    elif not faces:
        state, headline = "waiting", "Esperando un rostro"
    elif result is None:
        state, headline = "waiting", "Calculando identidad…"
    elif result.identified:
        state, headline = "identified", "Estudiante detectado"
        if len(faces) > 1:
            headline = "Varios rostros: identificando al más cercano"
        mapped, challenge_headline = _challenge_ui(challenge)
        if mapped is not None and challenge_headline is not None:
            state, headline = mapped, challenge_headline
    else:
        state, headline = "unknown", "Estudiante no identificado"

    photo_url = None
    student_id = None
    full_name = None
    program = None
    group_name = None
    score = None
    if result is not None and faces:
        score = round(result.score, 3)
        if result.identified:
            student_id = result.student_id
            full_name = result.full_name
            program = result.program
            group_name = result.group_name
            if student_id:
                photo_url = f"/api/photo/{student_id}"

    return KioskStatus(
        state=state,
        headline=headline,
        student_id=student_id,
        full_name=full_name,
        program=program,
        group_name=group_name,
        score=score,
        threshold=threshold,
        faces=len(faces),
        hands=len(detected_hands),
        gesture_number=gesture_number,
        challenge_target=challenge_target,
        challenge_step=challenge_step,
        challenge_total=challenge_total,
        remaining_seconds=remaining,
        fps=round(fps, 1),
        gallery_size=matcher.person_count,
        demo_mode=demo_mode,
        next_step=step,
        photo_url=photo_url,
        camera_ok=True,
        can_start_test=can_start_test,
        scanner_paused=scanner_paused,
    )
