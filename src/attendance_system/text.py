"""Texto UTF-8 en overlay. OpenCV Hershey no dibuja tildes (Pérez → P??rez)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\calibri.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
)


def _bgr_to_rgb(color: tuple[int, int, int]) -> tuple[int, int, int]:
    blue, green, red = color
    return (red, green, blue)


@lru_cache(maxsize=1)
def resolve_ui_font_path() -> Path | None:
    for path in _FONT_CANDIDATES:
        if path.exists():
            return path
    return None


@lru_cache(maxsize=16)
def load_ui_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = resolve_ui_font_path()
    if path is not None:
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def measure_text(text: str, size: int) -> tuple[int, int]:
    font = load_ui_font(size)
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = dummy.textbbox((0, 0), text, font=font, anchor="ls")
    return (max(1, right - left), max(1, bottom - top))


def draw_texts(
    frame: np.ndarray,
    items: list[tuple[str, tuple[int, int], tuple[int, int, int], int, int]],
) -> np.ndarray:
    """Dibuja varios textos UTF-8. org es esquina inferior-izquierda (como OpenCV)."""
    if not items:
        return frame
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    for text, org, color, size, stroke in items:
        draw.text(
            org,
            text,
            font=load_ui_font(size),
            fill=_bgr_to_rgb(color),
            stroke_width=stroke,
            stroke_fill=(0, 0, 0),
            anchor="ls",
        )
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
