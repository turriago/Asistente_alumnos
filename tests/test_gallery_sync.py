from __future__ import annotations

from pathlib import Path

import pytest
import cv2
import numpy as np

from attendance_system.gallery_sync import load_card_urls, thumbnail_data_url


def test_thumbnail_data_url_from_jpeg(tmp_path: Path) -> None:
    path = tmp_path / "TMP-0004.jpg"
    image = np.full((80, 80, 3), (40, 80, 160), dtype=np.uint8)
    assert cv2.imwrite(str(path), image)
    data_url = thumbnail_data_url(path)
    assert data_url is not None
    assert data_url.startswith("data:image/jpeg;base64,")
    assert len(data_url) > 80


def test_thumbnail_data_url_missing(tmp_path: Path) -> None:
    assert thumbnail_data_url(tmp_path / "nope.jpg") is None


def test_load_card_urls_reads_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cards = tmp_path / "supabase_cards.json"
    cards.write_text('{"TMP-0004": "https://example.test/card.jpg"}', encoding="utf-8")
    monkeypatch.setattr("attendance_system.gallery_sync.CARDS_FILE", cards)
    assert load_card_urls()["TMP-0004"] == "https://example.test/card.jpg"
