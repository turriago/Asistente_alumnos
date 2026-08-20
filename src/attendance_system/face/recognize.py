"""Demo Fase 4: identificar en vivo contra embeddings enrolados. Sin asistencia."""

from __future__ import annotations

import argparse
import sys
import time
from typing import NoReturn

import cv2
import numpy as np

from attendance_system.camera.capture import CameraUnavailableError, FpsMeter, open_preferred_camera
from attendance_system.camera.quality import assess_frame, enhance_if_dark, maybe_mirror
from attendance_system.config import PROJECT_ROOT, AppConfig, load_config
from attendance_system.database.session import create_db_engine, make_session_factory, session_scope
from attendance_system.drawing import draw_center_warning, draw_faces, draw_live_strip, draw_overlay
from attendance_system.face.demo import MAX_CAMERA_INDEX, _handle_camera_key
from attendance_system.face.detector import FaceDetector, FaceDetectorError
from attendance_system.face.embedder import EmbedderError, FaceEmbedder
from attendance_system.face.matcher import FaceMatcher, GalleryEntry, MatchResult
from attendance_system.face.model import FaceModelError
from attendance_system.face.types import DetectedFace
from attendance_system.logging_setup import get_logger, setup_logging
from attendance_system.students.service import StudentService

WINDOW_NAME = "Asistencia - Reconocimiento (Fase 4)"
QUIT_KEYS = {ord("q"), ord("Q"), 27}
RELOAD_KEYS = {ord("r"), ord("R")}


def _load_matcher(config: AppConfig, model_name: str) -> FaceMatcher:
    engine = create_db_engine(config.database.path)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        service = StudentService(session, config.database.photos_dir)
        enrolled = service.list_enrolled_faces(model_name=model_name)
    entries = [
        GalleryEntry(
            student_id=item.student_id,
            full_name=item.full_name,
            embedding=item.embedding,
            program=item.program,
            group_name=item.group_name,
        )
        for item in enrolled
    ]
    return FaceMatcher(entries, config.face.match_threshold)


def _status_lines(
    *,
    faces: list[DetectedFace],
    matcher: FaceMatcher,
    result: MatchResult | None,
    fps: float,
    camera_index: int,
    backend: str,
    dark: bool,
) -> tuple[list[str], bool, bool | None, list[str] | None]:
    waiting = True
    identified: bool | None = None
    labels: list[str] | None = None
    if dark:
        estado = "IMAGEN OSCURA"
    elif matcher.size == 0:
        estado = "SIN ROSTROS ENROLADOS"
    elif not faces:
        estado = "ESPERANDO ROSTRO"
    elif result is None:
        estado = "CALCULANDO"
        waiting = False
    elif result.identified:
        estado = "IDENTIFICADO"
        if len(faces) > 1:
            estado = "IDENTIFICADO (rostro más cercano)"
        waiting = False
        identified = True
        labels = [""] * len(faces)
        labels[0] = f"{result.full_name}  {result.score:.2f}"
    else:
        estado = "NO IDENTIFICADO"
        waiting = False
        identified = False
        labels = [""] * len(faces)
        labels[0] = f"NO IDENTIFICADO  {result.score:.2f}"

    score_line = "El rostro más grande se compara con 3 ángulos enrolados"
    if result is not None and faces:
        score_line = f"Similitud {result.score:.2f}   umbral {result.threshold:.2f}"
    elif matcher.size == 0:
        score_line = "Enrola 3 ángulos: python -m attendance_system.students.enroll --id 20260001"

    lines = [
        f"Estado: {estado}",
        f"Galería: {matcher.person_count} persona(s)  {matcher.size} toma(s)   Rostros: {len(faces)}",
        f"Cámara {camera_index}/{backend}   FPS {fps:.1f}",
        score_line,
        "R recargar galería | N cámara | Q salir",
    ]
    return lines, waiting or dark, identified, labels


def run_recognize_demo() -> int:
    config = load_config()
    logger = setup_logging(config.logging)

    try:
        detector = FaceDetector(config.face)
        embedder = FaceEmbedder(PROJECT_ROOT / "models")
    except (FaceModelError, FaceDetectorError, EmbedderError) as exc:
        logger.error("No se pudo iniciar detección/embedding: %s", exc)
        print(f"\n⚠️  {exc}\n", file=sys.stderr)
        return 1

    matcher = _load_matcher(config, embedder.model_name)
    logger.info("Galería cargada: %s embedding(s). Umbral=%.2f", matcher.size, matcher.threshold)
    if matcher.size == 0:
        print("No hay rostros enrolados. Enrola uno y pulsa R, o ejecuta:")
        print("  python -m attendance_system.students.enroll --id 20260001")

    try:
        camera, info = open_preferred_camera(config.camera)
    except CameraUnavailableError as exc:
        logger.error("Cámara no disponible: %s", exc)
        print(f"\n⚠️  Cámara no disponible.\n{exc}\n", file=sys.stderr)
        return 1

    fps_meter = FpsMeter()
    last_state = ""
    last_result: MatchResult | None = None
    last_face: DetectedFace | None = None
    last_match_at = 0.0
    print("Ventana: " + WINDOW_NAME)
    print("Un enrolado basta. Ponte frente a la cámara.")
    print("Si no te reconoce, baja FACE_MATCH_THRESHOLD (ahora más estricto que OpenCV 0.36).")
    print("Q salir. R recargar galería.")

    try:
        while True:
            result: MatchResult | None = None
            faces: list[DetectedFace] = []
            try:
                frame = camera.read()
                frame = maybe_mirror(frame, camera.settings.mirror)
                quality = assess_frame(frame, camera.settings.dark_mean_threshold)
                work = enhance_if_dark(frame, camera.settings.dark_mean_threshold)
                faces = detector.detect(work)
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
                            logger.warning("No se pudo calcular embedding en vivo: %s", exc)
                            last_result = None
                            last_face = None
                else:
                    last_result = None
                    last_face = None
                fps = fps_meter.tick()
                lines, waiting, identified, labels = _status_lines(
                    faces=faces,
                    matcher=matcher,
                    result=result,
                    fps=fps,
                    camera_index=info.index,
                    backend=info.backend,
                    dark=quality.dark,
                )
                state_key = lines[0]
                if state_key != last_state:
                    if result and result.identified:
                        logger.info("Identificado %s similitud=%.2f", result.student_id, result.score)
                    elif result and not result.identified:
                        logger.info("No identificado. Mejor similitud=%.2f", result.score)
                    else:
                        logger.info("%s", state_key)
                    last_state = state_key
                display = draw_faces(
                    work,
                    faces,
                    draw_landmarks=config.face.draw_landmarks,
                    labels=labels,
                    identified=identified,
                )
                display = draw_live_strip(display, quality.brightness)
                display = draw_overlay(display, lines, waiting=waiting)
                if quality.dark:
                    display = draw_center_warning(
                        display,
                        ["IMAGEN OSCURA", "Cierra la app Cámara de Windows", "Pulsa N"],
                    )
                cv2.imshow(WINDOW_NAME, display)
            except CameraUnavailableError as exc:
                logger.error("Cámara no disponible: %s", exc)
                canvas = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.imshow(WINDOW_NAME, draw_overlay(canvas, ["CÁMARA NO DISPONIBLE", str(exc)], error=True))

            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                logger.info("Demo de reconocimiento detenida por el usuario.")
                break
            if key in RELOAD_KEYS:
                matcher = _load_matcher(config, embedder.model_name)
                last_state = ""
                last_result = None
                last_face = None
                last_match_at = 0.0
                logger.info("Galería recargada: %s embedding(s).", matcher.size)
                print(f"Galería recargada: {matcher.size} enrolado(s).")
            try:
                info = _handle_camera_key(key, camera, info, fps_meter)
            except CameraUnavailableError as exc:
                logger.warning("No se pudo cambiar de cámara: %s", exc)
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        logger.info("Demo de reconocimiento interrumpida.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return 0


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Demo Fase 4: reconocimiento facial en vivo.")
    parser.parse_args()
    raise SystemExit(run_recognize_demo())


if __name__ == "__main__":
    main()
