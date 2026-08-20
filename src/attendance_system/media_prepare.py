"""Recortes de ficha a buena calidad. El kiosco local sigue usando 128px."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from attendance_system.students.inbox import IMAGE_SUFFIXES


def read_bgr(path: Path) -> np.ndarray | None:
    raw = np.fromfile(str(path), dtype=np.uint8)
    if raw.size == 0:
        return None
    frame = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        return None
    return frame


def encode_jpeg(image: np.ndarray, *, max_side: int, quality: int) -> bytes | None:
    if image.size == 0:
        return None
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest > max_side:
        scale = max_side / float(longest)
        image = cv2.resize(
            image,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return None
    return bytes(buffer)


def frame_from_video(path: Path) -> np.ndarray | None:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return None
    capture.set(cv2.CAP_PROP_POS_MSEC, 1000)
    ok, frame = capture.read()
    if not ok:
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = capture.read()
    capture.release()
    if not ok or frame is None or frame.size == 0:
        return None
    return frame


def card_jpeg_from_sources(photos: list[Path], videos: list[Path], fallback: Path | None) -> bytes | None:
    for photo in photos:
        if photo.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        image = read_bgr(photo)
        if image is not None:
            return encode_jpeg(image, max_side=720, quality=88)
    for video in videos:
        frame = frame_from_video(video)
        if frame is not None:
            return encode_jpeg(frame, max_side=720, quality=88)
    if fallback is not None:
        image = read_bgr(fallback)
        if image is not None:
            return encode_jpeg(image, max_side=720, quality=88)
    return None
