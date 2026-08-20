"""Bucle de cámara + reconocimiento para el kiosco. Un hilo, JPEG en RAM."""

from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from attendance_system.attendance import record_pass
from attendance_system.camera.capture import CameraUnavailableError, FpsMeter, open_preferred_camera
from attendance_system.camera.quality import assess_frame, enhance_if_dark, maybe_mirror
from attendance_system.challenge.manager import ChallengeManager
from attendance_system.config import PROJECT_ROOT, AppConfig
from attendance_system.database.session import create_db_engine, make_session_factory, session_scope
from attendance_system.drawing import draw_challenge_prompt, draw_faces, draw_gesture_number, draw_hands
from attendance_system.face.detector import FaceDetector, FaceDetectorError
from attendance_system.face.embedder import EmbedderError, FaceEmbedder
from attendance_system.face.matcher import FaceMatcher, GalleryEntry, MatchResult, select_kiosk_gallery
from attendance_system.face.model import FaceModelError
from attendance_system.face.types import DetectedFace
from attendance_system.gallery_sync import publish_web_gallery
from attendance_system.hands.detector import HandDetector, HandDetectorError
from attendance_system.hands.fingers import NumberSmoother, count_extended_fingers, read_number
from attendance_system.hands.focus import focus_settings_from_config, select_gesture_hands
from attendance_system.hands.model import HandsModelError
from attendance_system.hands.types import DetectedHand
from attendance_system.kiosk.status import KioskStatus, build_status
from attendance_system.logging_setup import get_logger
from attendance_system.students.service import StudentService

logger = get_logger("kiosk.engine")

_PLACEHOLDER = np.zeros((360, 640, 3), dtype=np.uint8)


def load_matcher(config: AppConfig, model_name: str) -> FaceMatcher:
    engine = create_db_engine(config.database.path)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        service = StudentService(session, config.database.photos_dir)
        enrolled = service.list_enrolled_faces(model_name=model_name)
    entries = select_kiosk_gallery(
        [
            GalleryEntry(
                student_id=item.student_id,
                full_name=item.full_name,
                embedding=item.embedding,
                program=item.program,
                group_name=item.group_name,
            )
            for item in enrolled
        ]
    )
    return FaceMatcher(entries, config.face.match_threshold)


def encode_jpeg(frame: np.ndarray, quality: int) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("No se pudo codificar JPEG.")
    return bytes(buffer)


class KioskEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._control = threading.Lock()
        self._thread: threading.Thread | None = None
        self._jpeg = encode_jpeg(_PLACEHOLDER, config.kiosk.jpeg_quality)
        self._challenge = ChallengeManager(config.challenge)
        self._paused = False
        self._ready_student_id: str | None = None
        self._attendance_logged: set[str] = set()
        self._status = build_status(
            faces=[],
            matcher=FaceMatcher([], config.face.match_threshold),
            result=None,
            fps=0.0,
            dark=False,
            demo_mode=config.demo_mode,
            camera_ok=False,
            camera_error="Iniciando cámara…",
        )

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="kiosk-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    def latest_jpeg(self) -> bytes:
        with self._lock:
            return self._jpeg

    def latest_status(self) -> KioskStatus:
        with self._lock:
            return self._status

    def start_challenge(self) -> dict[str, object]:
        with self._control:
            if self._paused:
                return {"ok": False, "error": "La prueba ya terminó. Pulsa Nueva prueba."}
            student_id = self._ready_student_id
            if not student_id:
                return {"ok": False, "error": "Identifícate primero."}
            started = self._challenge.request_start(
                now=time.monotonic(),
                student_id=student_id,
            )
        if not started:
            return {"ok": False, "error": "La prueba ya está en curso."}
        return {"ok": True}

    def reset_scan(self) -> dict[str, object]:
        with self._control:
            self._challenge.reset()
            self._paused = False
        return {"ok": True}

    def _sync_web_gallery(self) -> None:
        try:
            result = publish_web_gallery(self.config)
            logger.info("Galería web: %s", result.get("message"))
        except Exception as exc:
            logger.warning("No se pudo publicar la galería web: %s", exc)

    def _record_attendance(self, student_id: str, full_name: str) -> None:
        try:
            record_pass(self.config, student_id=student_id, full_name=full_name, source="kiosk")
        except Exception as exc:
            logger.warning("No se pudo registrar asistencia: %s", exc)

    def _publish(self, frame: np.ndarray, status: KioskStatus) -> None:
        jpeg = encode_jpeg(frame, self.config.kiosk.jpeg_quality)
        with self._lock:
            self._jpeg = jpeg
            self._status = status

    def _run(self) -> None:
        config = self.config
        try:
            detector = FaceDetector(config.face)
            embedder = FaceEmbedder(PROJECT_ROOT / "models")
            matcher = load_matcher(config, embedder.model_name)
        except (FaceModelError, FaceDetectorError, EmbedderError) as exc:
            logger.error("No se pudo iniciar el kiosco: %s", exc)
            self._publish(_PLACEHOLDER, build_status(
                faces=[],
                matcher=FaceMatcher([], config.face.match_threshold),
                result=None,
                fps=0.0,
                dark=False,
                demo_mode=config.demo_mode,
                camera_ok=False,
                camera_error=str(exc),
            ))
            return

        logger.info("Galería del kiosco: %s embedding(s).", matcher.size)
        threading.Thread(target=self._sync_web_gallery, daemon=True, name="web-gallery").start()
        hand_detector: HandDetector | None = None
        hands_error: str | None = None
        try:
            hand_detector = HandDetector(config.hands)
        except (HandDetectorError, HandsModelError) as exc:
            hands_error = str(exc)
            logger.error("Manos no disponibles: %s", exc)

        camera = None
        last_result: MatchResult | None = None
        last_face: DetectedFace | None = None
        last_match_at = 0.0
        last_hands: list[DetectedHand] = []
        last_hands_at = 0.0
        number_smoother = NumberSmoother(config.hands.number_stable_ms)
        fps_meter = FpsMeter()
        try:
            camera, _info = open_preferred_camera(config.camera)
        except CameraUnavailableError as exc:
            logger.error("Cámara no disponible: %s", exc)
            self._publish(_PLACEHOLDER, build_status(
                faces=[],
                matcher=matcher,
                result=None,
                fps=0.0,
                dark=False,
                demo_mode=config.demo_mode,
                camera_ok=False,
                camera_error=str(exc),
                hands_error=hands_error,
            ))
            if hand_detector is not None:
                hand_detector.close()
            return

        try:
            while not self._stop.is_set():
                try:
                    with self._control:
                        paused = self._paused
                    if paused:
                        try:
                            camera.read()
                        except CameraUnavailableError:
                            raise
                        time.sleep(0.08)
                        continue
                    frame = camera.read()
                    frame = maybe_mirror(frame, camera.settings.mirror)
                    quality = assess_frame(frame, camera.settings.dark_mean_threshold)
                    work = enhance_if_dark(frame, camera.settings.dark_mean_threshold)
                    faces = detector.detect(work)
                    result: MatchResult | None = None
                    if matcher.size > 0 and faces and not quality.dark:
                        now = time.monotonic()
                        elapsed_ms = (now - last_match_at) * 1000.0
                        primary = faces[0]
                        reuse = (
                            last_result is not None
                            and last_face is not None
                            and elapsed_ms < config.face.match_interval_ms
                            and primary.iou(last_face) >= 0.5
                        )
                        if reuse:
                            result = last_result
                        else:
                            try:
                                embedding = embedder.embed(work, primary)
                                result = matcher.match(embedding)
                                last_result = result
                                last_face = primary
                                last_match_at = now
                            except EmbedderError as exc:
                                logger.warning("Embedding en vivo falló: %s", exc)
                                last_result = None
                                last_face = None
                    else:
                        last_result = None
                        last_face = None
                    if hand_detector is None or quality.dark:
                        last_hands = []
                        number_smoother.reset()
                        gesture_number = None
                        finger_counts: tuple[int, ...] = ()
                        active: list[bool] = []
                        focused: list[DetectedHand] = []
                    else:
                        now = time.monotonic()
                        interval = config.hands.detect_interval_ms
                        if interval == 0 or last_hands_at == 0.0 or (now - last_hands_at) * 1000.0 >= interval:
                            last_hands = hand_detector.detect(
                                work, mirrored=camera.settings.mirror
                            )
                            last_hands_at = now
                        focused = select_gesture_hands(
                            last_hands,
                            faces,
                            settings=focus_settings_from_config(config.hands),
                        )
                        focused_ids = {id(hand) for hand in focused}
                        active = [id(hand) in focused_ids for hand in last_hands]
                        reading = read_number(
                            focused,
                            finger_ratio=config.hands.finger_extend_ratio,
                            thumb_ratio=config.hands.thumb_extend_ratio,
                        )
                        finger_counts = tuple(
                            count_extended_fingers(
                                hand,
                                finger_ratio=config.hands.finger_extend_ratio,
                                thumb_ratio=config.hands.thumb_extend_ratio,
                            )
                            if is_on
                            else 0
                            for hand, is_on in zip(last_hands, active)
                        )
                        if not focused:
                            number_smoother.reset()
                            gesture_number = None
                        else:
                            gesture_number = number_smoother.update(reading.number, now)
                    now = time.monotonic()
                    identified_ok = (
                        result is not None
                        and result.identified
                        and not quality.dark
                    )
                    with self._control:
                        if identified_ok and result is not None and result.student_id:
                            self._ready_student_id = result.student_id
                        elif self._challenge.idle:
                            self._ready_student_id = None
                        challenge_view = self._challenge.observe(
                            now=now,
                            student_id=result.student_id if identified_ok else None,
                            identified=bool(identified_ok),
                            gesture_number=gesture_number if identified_ok else None,
                        )
                        if challenge_view.state == "success":
                            self._paused = True
                            sid = challenge_view.student_id
                            if sid and sid not in self._attendance_logged:
                                self._attendance_logged.add(sid)
                                name = (result.full_name if result and result.full_name else "") or ""
                                threading.Thread(
                                    target=self._record_attendance,
                                    args=(sid, name),
                                    daemon=True,
                                    name="attendance-post",
                                ).start()
                    fps = fps_meter.tick()
                    identified = result.identified if result is not None else None
                    labels = [""] * len(faces)
                    if result is not None and faces:
                        labels[0] = (
                            f"{result.full_name}  {result.score:.2f}"
                            if result.identified
                            else f"NO IDENTIFICADO  {result.score:.2f}"
                        )
                    display = draw_faces(
                        work,
                        faces,
                        draw_landmarks=config.face.draw_landmarks,
                        labels=labels,
                        identified=identified,
                    )
                    display = draw_hands(
                        display,
                        last_hands,
                        finger_counts=finger_counts,
                        active=active,
                    )
                    display = draw_gesture_number(display, gesture_number)
                    display = draw_challenge_prompt(
                        display,
                        target=challenge_view.target,
                        step=challenge_view.step if challenge_view.sequence else None,
                        total=challenge_view.total if challenge_view.sequence else None,
                        remaining=challenge_view.remaining_seconds,
                        waiting_release=challenge_view.waiting_release,
                        done=challenge_view.state == "success",
                        failed=challenge_view.state == "failed",
                    )
                    status = build_status(
                        faces=faces,
                        matcher=matcher,
                        result=result,
                        fps=fps,
                        dark=quality.dark,
                        demo_mode=config.demo_mode,
                        camera_ok=True,
                        hands=focused,
                        hands_error=hands_error,
                        gesture_number=gesture_number,
                        challenge=challenge_view,
                    )
                    self._publish(display, status)
                except CameraUnavailableError as exc:
                    logger.error("Cámara perdida: %s", exc)
                    self._publish(_PLACEHOLDER, build_status(
                        faces=[],
                        matcher=matcher,
                        result=None,
                        fps=0.0,
                        dark=False,
                        demo_mode=config.demo_mode,
                        camera_ok=False,
                        camera_error=str(exc),
                        hands_error=hands_error,
                    ))
                    time.sleep(0.4)
        finally:
            camera.release()
            if hand_detector is not None:
                hand_detector.close()
            logger.info("Motor del kiosco detenido.")
