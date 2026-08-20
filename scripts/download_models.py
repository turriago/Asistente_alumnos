"""Descarga YuNet, SFace y Hand Landmarker en models/. No sube pesos a Git."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from attendance_system.config import PROJECT_ROOT, load_config
from attendance_system.face.model import FaceModelError, ensure_sface_model, ensure_yunet_model
from attendance_system.hands.model import HandsModelError, ensure_hand_landmarker
from attendance_system.logging_setup import setup_logging


def main() -> None:
    config = load_config()
    setup_logging(config.logging)
    try:
        yunet = ensure_yunet_model(config.face.model_path, auto_download=True)
        sface = ensure_sface_model(PROJECT_ROOT / "models", auto_download=True)
        hands = ensure_hand_landmarker(config.hands.model_path, auto_download=True)
    except (FaceModelError, HandsModelError) as exc:
        print(f"⚠️  {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"YuNet: {yunet}")
    print(f"SFace: {sface}")
    print(f"Hands: {hands}")


if __name__ == "__main__":
    main()
