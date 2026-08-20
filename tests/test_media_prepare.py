from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from attendance_system.media_prepare import card_jpeg_from_sources, encode_jpeg


def test_encode_jpeg_limits_long_side() -> None:
    image = np.zeros((1200, 800, 3), dtype=np.uint8)
    data = encode_jpeg(image, max_side=720, quality=80)
    assert data is not None
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert max(decoded.shape[0], decoded.shape[1]) == 720


def test_card_jpeg_from_photo(tmp_path: Path) -> None:
    path = tmp_path / "1_cara.jpg"
    image = np.full((400, 300, 3), (20, 40, 80), dtype=np.uint8)
    assert cv2.imwrite(str(path), image)
    card = card_jpeg_from_sources([path], [], None)
    assert card is not None
    assert card[:2] == b"\xff\xd8"
