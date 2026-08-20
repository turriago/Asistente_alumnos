from __future__ import annotations

import numpy as np

from attendance_system.camera.quality import (
    enhance_if_dark,
    is_dark_frame,
    maybe_mirror,
    preview_score,
    selection_score,
)
from attendance_system.drawing import draw_center_warning, draw_live_strip


def test_dark_frame_detected() -> None:
    dark = np.zeros((40, 40, 3), dtype=np.uint8)
    bright = np.full((40, 40, 3), 200, dtype=np.uint8)
    assert is_dark_frame(dark, 45.0) is True
    assert is_dark_frame(bright, 45.0) is False


def test_color_webcam_scores_higher_than_gray_ir() -> None:
    gray = np.full((40, 40, 3), 80, dtype=np.uint8)
    color = np.zeros((40, 40, 3), dtype=np.uint8)
    color[:, :, 2] = 180
    color[:, :, 1] = 40
    assert preview_score(color) > preview_score(gray)


def test_enhance_dark_changes_pixels_but_keeps_shape() -> None:
    dark = np.full((32, 32, 3), 20, dtype=np.uint8)
    out = enhance_if_dark(dark, 45.0)
    assert out.shape == dark.shape
    assert not np.array_equal(out, dark)


def test_mirror_flips_horizontally() -> None:
    frame = np.zeros((10, 12, 3), dtype=np.uint8)
    frame[:, 0] = 255
    mirrored = maybe_mirror(frame, True)
    assert mirrored[0, -1, 0] == 255
    assert np.array_equal(maybe_mirror(frame, False), frame)


def test_bright_frame_outranks_dark_colorful_one() -> None:
    dark = np.zeros((40, 40, 3), dtype=np.uint8)
    dark[:, :, 2] = 40
    bright = np.full((40, 40, 3), 140, dtype=np.uint8)
    assert selection_score(bright, 45.0) > selection_score(dark, 45.0)


def test_live_strip_and_warning_draw() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    warned = draw_center_warning(frame, ["NO SE VE LA WEBCAM RGB"])
    strip = draw_live_strip(frame, 40)
    assert warned.shape == frame.shape
    assert strip.shape == frame.shape
    assert not np.array_equal(warned, frame)
