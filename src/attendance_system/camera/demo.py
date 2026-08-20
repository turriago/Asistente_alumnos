"""Demo Fase 1: PC → cámara → vídeo, con FPS, resolución y errores visibles."""

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
from attendance_system.drawing import draw_center_warning, draw_live_strip, draw_overlay
from attendance_system.logging_setup import get_logger, setup_logging

WINDOW_NAME = "Asistencia - Cámara (Fase 1)"
QUIT_KEYS = {ord("q"), ord("Q"), 27}  # q o Escape
MAX_CAMERA_INDEX = 4


def _status_lines(info: CameraInfo, fps: float, demo_mode: bool, dark: bool) -> list[str]:
    estado = "IMAGEN OSCURA" if dark else "CÁMARA OK"
    lines = [
        f"Estado: {estado}",
        f"Resolución: {info.width}x{info.height}  (pedida {info.requested_width}x{info.requested_height})",
        f"FPS real: {fps:.1f}   Índice: {info.index}   Backend: {info.backend}",
        "Teclas: N cámara | B backend | Q o ESC salir",
    ]
    if demo_mode:
        lines.insert(1, "DEMO_MODE=true")
    return lines


def _show_error_frame(message: str, width: int, height: int) -> None:
    canvas = np.zeros((max(height, 360), max(width, 640), 3), dtype=np.uint8)
    canvas[:] = (30, 30, 30)
    lines = ["CÁMARA NO DISPONIBLE", message, "Reconectando...  Q o ESC para salir"]
    display = draw_overlay(canvas, lines, error=True)
    cv2.imshow(WINDOW_NAME, display)


def run_camera_demo() -> int:
    config = load_config()
    logger = setup_logging(config.logging)

    try:
        camera, info = open_preferred_camera(config.camera)
    except CameraUnavailableError as exc:
        logger.error("Cámara no disponible: %s", exc)
        print(f"\n⚠️  Cámara no disponible.\n{exc}\n", file=sys.stderr)
        print("Sugerencia: pulsa N en la demo o prueba CAMERA_INDEX=1", file=sys.stderr)
        return 1

    fps_meter = FpsMeter()
    logger.info("Demo de cámara iniciada. Cierra con Q o ESC. Índice=%s", info.index)
    print("Cámara abierta. Ventana: " + WINDOW_NAME)
    print(f"Índice {info.index}. Si ves negro, pulsa N. Q o ESC para salir.")

    try:
        while True:
            try:
                frame = camera.read()
                frame = maybe_mirror(frame, camera.settings.mirror)
                quality = assess_frame(frame, camera.settings.dark_mean_threshold)
                work = enhance_if_dark(frame, camera.settings.dark_mean_threshold)
                fps = fps_meter.tick()
                display = draw_overlay(
                    work,
                    _status_lines(info, fps, config.demo_mode, quality.dark),
                    waiting=quality.dark,
                )
                display = draw_live_strip(display, quality.brightness)
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
                _show_error_frame(str(exc), config.camera.width, config.camera.height)
                try:
                    info = camera.reconnect()
                    fps_meter.reset()
                    logger.info("Cámara reconectada.")
                except CameraUnavailableError as reconnect_exc:
                    logger.error("No se pudo reconectar la cámara: %s", reconnect_exc)

            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                logger.info("Demo de cámara detenida por el usuario.")
                break
            target = None
            if key in {ord("n"), ord("N")}:
                target = (info.index + 1) % (MAX_CAMERA_INDEX + 1)
            elif key in {ord("p"), ord("P")}:
                target = (info.index - 1) % (MAX_CAMERA_INDEX + 1)
            elif ord("0") <= key <= ord("4"):
                target = key - ord("0")
            if target is not None and target != info.index:
                try:
                    info = camera.switch_index(target)
                    fps_meter.reset()
                except CameraUnavailableError as exc:
                    logger.warning("No se pudo cambiar de cámara: %s", exc)
            elif key in {ord("b"), ord("B")}:
                other = "dshow" if camera.settings.backend == "msmf" else "msmf"
                try:
                    info = camera.switch_backend(other)
                    fps_meter.reset()
                except CameraUnavailableError as exc:
                    logger.warning("No se pudo cambiar de backend: %s", exc)
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                logger.info("Ventana de cámara cerrada.")
                break
    except KeyboardInterrupt:
        logger.info("Demo de cámara interrumpida.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return 0


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Demo Fase 1: webcam del PC.")
    parser.parse_args()
    raise SystemExit(run_camera_demo())


if __name__ == "__main__":
    main()
