"""Demo Fase 7: manos + número 1–10. Sin desafío ni asistencia."""

from __future__ import annotations

import argparse
import sys
import time
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
    draw_gesture_number,
    draw_hands,
    draw_live_strip,
    draw_overlay,
)
from attendance_system.face.demo import QUIT_KEYS, _handle_camera_key
from attendance_system.hands.detector import HandDetector, HandDetectorError
from attendance_system.hands.fingers import NumberSmoother, read_number
from attendance_system.hands.model import HandsModelError
from attendance_system.hands.types import DetectedHand
from attendance_system.logging_setup import setup_logging

WINDOW_NAME = "Asistencia - Numeros 1-10 (Fase 7)"


def _status_lines(
    info: CameraInfo,
    fps: float,
    hands: list[DetectedHand],
    number: int | None,
    dark: bool,
    demo_mode: bool,
) -> tuple[list[str], bool]:
    if dark:
        estado = "IMAGEN OSCURA"
    elif number is not None:
        estado = f"NÚMERO {number}"
    elif not hands:
        estado = "ESPERANDO MANOS"
    else:
        estado = "ESTIRA LOS DEDOS  (1–10)"
    lines = [
        f"Estado: {estado}",
        "1–5 con una mano. 3 números seguidos.",
        f"Cámara index={info.index} {info.backend}   {info.width}x{info.height}   FPS {fps:.1f}",
        "Teclas: N cámara | B backend | Q salir",
    ]
    if demo_mode:
        lines.insert(1, "DEMO_MODE=true")
    return lines, dark or number is None


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Demo de números 1–10 con las manos.")
    parser.parse_args()
    config = load_config()
    setup_logging(config.logging)

    try:
        detector = HandDetector(config.hands)
    except (HandDetectorError, HandsModelError) as exc:
        print(f"⚠️  {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    fps_meter = FpsMeter()
    smoother = NumberSmoother(config.hands.number_stable_ms)
    camera = None
    info: CameraInfo | None = None
    try:
        try:
            camera, info = open_preferred_camera(config.camera)
        except CameraUnavailableError as exc:
            print(f"⚠️  {exc}", file=sys.stderr)
            canvas = np.zeros((360, 640, 3), dtype=np.uint8)
            canvas[:] = (30, 30, 30)
            display = draw_overlay(canvas, ["Cámara no disponible", str(exc), "Q para salir"], error=True)
            cv2.imshow(WINDOW_NAME, display)
            while True:
                key = cv2.waitKey(50) & 0xFF
                if key in QUIT_KEYS:
                    break
            raise SystemExit(1) from exc

        while True:
            try:
                frame = camera.read()
            except CameraUnavailableError as exc:
                display = draw_center_warning(
                    np.zeros((info.height, info.width, 3), dtype=np.uint8),
                    ["Cámara perdida", str(exc)],
                )
                cv2.imshow(WINDOW_NAME, display)
                key = cv2.waitKey(50) & 0xFF
                if key in QUIT_KEYS:
                    break
                continue
            frame = maybe_mirror(frame, camera.settings.mirror)
            quality = assess_frame(frame, camera.settings.dark_mean_threshold)
            work = enhance_if_dark(frame, camera.settings.dark_mean_threshold)
            hands = [] if quality.dark else detector.detect(work, mirrored=camera.settings.mirror)
            if quality.dark:
                smoother.reset()
                number = None
                counts: tuple[int, ...] = ()
            else:
                reading = read_number(
                    hands,
                    finger_ratio=config.hands.finger_extend_ratio,
                    thumb_ratio=config.hands.thumb_extend_ratio,
                )
                counts = reading.per_hand
                number = smoother.update(reading.number, time.monotonic())
            fps = fps_meter.tick()
            lines, waiting = _status_lines(info, fps, hands, number, quality.dark, config.demo_mode)
            display = draw_hands(work, hands, finger_counts=counts)
            display = draw_gesture_number(display, number)
            display = draw_overlay(display, lines, waiting=waiting)
            display = draw_live_strip(display, quality.brightness)
            cv2.imshow(WINDOW_NAME, display)
            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                break
            info = _handle_camera_key(key, camera, info, fps_meter)
    finally:
        detector.close()
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()
    raise SystemExit(0)


if __name__ == "__main__":
    main()
