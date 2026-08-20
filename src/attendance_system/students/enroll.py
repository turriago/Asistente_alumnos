"""Demo Fase 3: enrolar 3 ángulos de un estudiante. No identifica en vivo."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

import cv2
import numpy as np

from attendance_system.camera.capture import CameraUnavailableError, FpsMeter, open_preferred_camera
from attendance_system.camera.quality import assess_frame, enhance_if_dark, maybe_mirror
from attendance_system.config import PROJECT_ROOT, load_config
from attendance_system.database.session import create_db_engine, make_session_factory, session_scope
from attendance_system.drawing import draw_center_warning, draw_faces, draw_live_strip, draw_overlay
from attendance_system.face.demo import _handle_camera_key
from attendance_system.face.detector import FaceDetector, FaceDetectorError
from attendance_system.face.embedder import EmbedderError, FaceEmbedder
from attendance_system.face.model import FaceModelError
from attendance_system.face.types import DetectedFace
from attendance_system.logging_setup import get_logger, setup_logging
from attendance_system.students.seed import seed_students
from attendance_system.students.service import StudentNotFoundError, StudentService

WINDOW_NAME = "Asistencia - Enrolamiento (3 ángulos)"
QUIT_KEYS = {ord("q"), ord("Q"), 27}
CAPTURE_KEYS = {ord("e"), ord("E")}


def run_enroll_demo(student_id: str) -> int:
    config = load_config()
    logger = setup_logging(config.logging)
    seed_students()
    poses = config.face.enroll_poses

    engine = create_db_engine(config.database.path)
    factory = make_session_factory(engine)

    with session_scope(factory) as session:
        service = StudentService(session, config.database.photos_dir)
        try:
            student = service.require(student_id)
        except StudentNotFoundError as exc:
            logger.error("%s", exc)
            print(f"\n⚠️  {exc}\nIDs de demo: 20260001 a 20260005.\n", file=sys.stderr)
            return 1

    try:
        detector = FaceDetector(config.face)
        embedder = FaceEmbedder(PROJECT_ROOT / "models")
    except (FaceModelError, FaceDetectorError, EmbedderError) as exc:
        logger.error("No se pudo iniciar detección/embedding: %s", exc)
        print(f"\n⚠️  {exc}\n", file=sys.stderr)
        return 1

    try:
        camera, info = open_preferred_camera(config.camera)
    except CameraUnavailableError as exc:
        logger.error("Cámara no disponible: %s", exc)
        print(f"\n⚠️  Cámara no disponible.\n{exc}\n", file=sys.stderr)
        return 1

    fps_meter = FpsMeter()
    faces: list[DetectedFace] = []
    shots: list[tuple[np.ndarray, DetectedFace, np.ndarray]] = []
    print(f"Enrolando a {student.full_name} ({student.student_id}).")
    print("Tres tomas: frente, izquierda, derecha. Un solo rostro. Pulsa E en cada pose.")
    print("Si tienes cámara profesional, pulsa N hasta verla. Q cancela.")

    try:
        while True:
            pose = poses[len(shots)]
            try:
                frame = camera.read()
                frame = maybe_mirror(frame, camera.settings.mirror)
                quality = assess_frame(frame, camera.settings.dark_mean_threshold)
                work = enhance_if_dark(frame, camera.settings.dark_mean_threshold)
                faces = detector.detect(work)
                fps = fps_meter.tick()
                can_enroll = len(faces) == 1
                estado = f"LISTO: {pose}" if can_enroll else "NECESITO UN SOLO ROSTRO"
                lines = [
                    f"Estado: {estado}",
                    f"Toma {len(shots) + 1}/{len(poses)}  →  {pose}",
                    f"Estudiante: {student.full_name}  ID {student.student_id}",
                    f"Rostros: {len(faces)}   Cámara {info.index}/{info.backend}   FPS {fps:.1f}",
                    "E capturar esta pose | N cámara | Q cancelar",
                ]
                display = draw_faces(work, faces, draw_landmarks=config.face.draw_landmarks)
                display = draw_live_strip(display, quality.brightness)
                display = draw_overlay(display, lines, waiting=not can_enroll)
                if quality.dark:
                    display = draw_center_warning(
                        display,
                        ["IMAGEN OSCURA", "Cierra la app Cámara de Windows", "Pulsa N para otra cámara"],
                    )
                cv2.imshow(WINDOW_NAME, display)
            except CameraUnavailableError as exc:
                logger.error("Cámara no disponible: %s", exc)
                canvas = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.imshow(WINDOW_NAME, draw_overlay(canvas, ["CÁMARA NO DISPONIBLE", str(exc)], error=True))

            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                break
            try:
                info = _handle_camera_key(key, camera, info, fps_meter)
            except CameraUnavailableError as exc:
                logger.warning("No se pudo cambiar de cámara: %s", exc)
            if key in CAPTURE_KEYS:
                if len(faces) != 1:
                    logger.warning("Toma rechazada: se necesita exactamente un rostro.")
                    continue
                try:
                    embedding = embedder.embed(work, faces[0])
                    shots.append((work.copy(), faces[0], embedding))
                    logger.info("Toma %s/%s (%s) guardada en RAM.", len(shots), len(poses), pose)
                    print(f"Toma {len(shots)}/{len(poses)} ({pose}) OK.")
                    if len(shots) >= len(poses):
                        with session_scope(factory) as session:
                            service = StudentService(session, config.database.photos_dir)
                            updated = service.enroll_faces(
                                student.student_id,
                                shots,
                                model_name=embedder.model_name,
                            )
                        print(
                            f"✅ {len(shots)} ángulos guardados para {updated.full_name}. "
                            "Miniatura local, no se sube a Git."
                        )
                        return 0
                except EmbedderError as exc:
                    logger.warning("No se pudo calcular embedding: %s", exc)
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        logger.info("Enrolamiento interrumpido.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return 0


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Enrolar 3 ángulos de un estudiante de demo.")
    parser.add_argument("--id", default="20260001", help="ID ficticio, por defecto 20260001 (Ana Pérez Demo).")
    args = parser.parse_args()
    raise SystemExit(run_enroll_demo(args.id))


if __name__ == "__main__":
    main()
