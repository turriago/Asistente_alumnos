"""Demo Fase 2: cámara + detección facial. No identifica personas."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

import cv2
import numpy as np

from attendance_system.camera.capture import (
    CameraInfo,
    CameraUnavailableError,
    FpsMeter,
    open_preferred_camera,
)
from attendance_system.camera.quality import assess_frame, enhance_if_dark, maybe_mirror
from attendance_system.config import load_config
from attendance_system.drawing import (
    draw_center_warning,
    draw_faces,
    draw_live_strip,
    draw_overlay,
)
from attendance_system.face.detector import FaceDetector, FaceDetectorError
from attendance_system.face.model import FaceModelError
from attendance_system.face.types import DetectedFace
from attendance_system.logging_setup import get_logger, setup_logging

WINDOW_NAME = "Asistencia - Deteccion facial (Fase 2)"
QUIT_KEYS = {ord("q"), ord("Q"), 27}
MAX_CAMERA_INDEX = 4


def _status_lines(
    info: CameraInfo,
    fps: float,
    demo_mode: bool,
    faces: list[DetectedFace],
    score_threshold: float,
    dark: bool,
) -> tuple[list[str], bool]:
    waiting = len(faces) == 0
    if dark:
        estado = "IMAGEN OSCURA"
    elif waiting:
        estado = "ESPERANDO ROSTRO"
    elif len(faces) == 1:
        estado = "ROSTRO DETECTADO"
    else:
        estado = f"VARIOS ROSTROS ({len(faces)})"

    score_line = (
        f"Mejor score: {faces[0].score:.2f}   umbral: {score_threshold:.2f}"
        if faces
        else f"Acércate a la cámara   umbral: {score_threshold:.2f}"
    )
    lines = [
        f"Estado: {estado}",
        f"Rostros: {len(faces)}   (sin identificar)",
        f"Cámara index={info.index} {info.backend}   {info.width}x{info.height}   FPS {fps:.1f}",
        score_line,
        "Teclas: N cámara | B backend | Q salir",
    ]
    if demo_mode:
        lines.insert(1, "DEMO_MODE=true")
    return lines, waiting or dark


def _show_error_frame(title: str, message: str, width: int, height: int) -> None:
    canvas = np.zeros((max(height, 360), max(width, 640), 3), dtype=np.uint8)
    canvas[:] = (30, 30, 30)
    display = draw_overlay(canvas, [title, message, "Q o ESC para salir"], error=True)
    cv2.imshow(WINDOW_NAME, display)


def _handle_camera_key(key: int, camera, info: CameraInfo, fps_meter: FpsMeter) -> CameraInfo:
    target: int | None = None
    if key in {ord("n"), ord("N")}:
        target = (info.index + 1) % (MAX_CAMERA_INDEX + 1)
    elif key in {ord("p"), ord("P")}:
        target = (info.index - 1) % (MAX_CAMERA_INDEX + 1)
    elif ord("0") <= key <= ord(str(MAX_CAMERA_INDEX)):
        target = key - ord("0")
    elif key in {ord("b"), ord("B")}:
        other = "dshow" if camera.settings.backend == "msmf" else "msmf"
        new_info = camera.switch_backend(other)
        fps_meter.reset()
        return new_info
    if target is None or target == info.index:
        return info
    new_info = camera.switch_index(target)
    fps_meter.reset()
    return new_info


def run_face_demo() -> int:
    config = load_config()
    logger = setup_logging(config.logging)

    try:
        detector = FaceDetector(config.face)
    except (FaceModelError, FaceDetectorError) as exc:
        logger.error("Detector facial no disponible: %s", exc)
        print(f"\n⚠️  Modelo de detección no disponible.\n{exc}\n", file=sys.stderr)
        return 1

    try:
        camera, info = open_preferred_camera(config.camera)
    except CameraUnavailableError as exc:
        logger.error("Cámara no disponible: %s", exc)
        print(f"\n⚠️  Cámara no disponible.\n{exc}\n", file=sys.stderr)
        return 1

    fps_meter = FpsMeter()
    logger.info("Demo de detección facial iniciada. Cámara index=%s.", info.index)
    print("Ventana: " + WINDOW_NAME)
    print(f"Cámara en uso: índice {info.index}. Si ves negro, pulsa N.")
    print("N = siguiente cámara. P = anterior. 0-4 = índice. Q = salir.")

    last_count = -1
    try:
        while True:
            try:
                frame = camera.read()
                frame = maybe_mirror(frame, camera.settings.mirror)
                quality = assess_frame(frame, camera.settings.dark_mean_threshold)
                work = enhance_if_dark(frame, camera.settings.dark_mean_threshold)
                faces = detector.detect(work)
                if len(faces) != last_count:
                    if not faces:
                        logger.info("Ningún rostro en cámara.")
                    else:
                        logger.info("Rostros detectados: %s (sin identificar).", len(faces))
                    last_count = len(faces)
                fps = fps_meter.tick()
                annotated = draw_faces(work, faces, draw_landmarks=config.face.draw_landmarks)
                annotated = draw_live_strip(annotated, quality.brightness)
                lines, waiting = _status_lines(
                    info,
                    fps,
                    config.demo_mode,
                    faces,
                    config.face.score_threshold,
                    quality.dark,
                )
                display = draw_overlay(annotated, lines, waiting=waiting)
                if quality.dark:
                    display = draw_center_warning(
                        display,
                        [
                            "NO SE VE LA WEBCAM RGB",
                            "Pulsa N para cambiar de cámara",
                            "Quita la tapa de la lente",
                        ],
                    )
                cv2.imshow(WINDOW_NAME, display)
            except CameraUnavailableError as exc:
                logger.error("Cámara no disponible durante la captura: %s", exc)
                _show_error_frame("CÁMARA NO DISPONIBLE", str(exc), config.camera.width, config.camera.height)
                try:
                    info = camera.reconnect()
                    fps_meter.reset()
                    logger.info("Cámara reconectada.")
                except CameraUnavailableError as reconnect_exc:
                    logger.error("No se pudo reconectar la cámara: %s", reconnect_exc)

            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                logger.info("Demo de detección detenida por el usuario.")
                break
            try:
                info = _handle_camera_key(key, camera, info, fps_meter)
            except CameraUnavailableError as exc:
                logger.warning("No se pudo cambiar de cámara: %s", exc)
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                logger.info("Ventana de detección cerrada.")
                break
    except KeyboardInterrupt:
        logger.info("Demo de detección interrumpida.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return 0


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Demo Fase 2: detección facial.")
    parser.parse_args()
    raise SystemExit(run_face_demo())


if __name__ == "__main__":
    main()
