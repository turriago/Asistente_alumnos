"""Atajo para ejecutar la demo de cámara de la Fase 1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from attendance_system.camera.demo import main

if __name__ == "__main__":
    main()
