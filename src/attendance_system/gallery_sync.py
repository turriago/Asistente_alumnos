"""Miniaturas locales → JSON para el celular. No va a GitHub."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import cv2

from attendance_system.config import PROJECT_ROOT, AppConfig, load_config
from attendance_system.database.session import create_db_engine, make_session_factory, session_scope
from attendance_system.face.embedder import MODEL_NAME
from attendance_system.face.matcher import GalleryEntry, select_kiosk_gallery
from attendance_system.logging_setup import get_logger
from attendance_system.students.service import StudentService

logger = get_logger("gallery_sync")

RUNTIME_DIR = PROJECT_ROOT / "web" / "runtime"
RUNTIME_FILE = RUNTIME_DIR / "gallery.json"


def thumbnail_data_url(path: Path) -> str | None:
    if not path.is_file():
        return None
    image = cv2.imread(str(path))
    if image is None or image.size == 0:
        return None
    small = cv2.resize(image, (96, 96), interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    if not ok:
        return None
    encoded = base64.b64encode(bytes(buffer)).decode("ascii")
    return "data:image/jpeg;base64," + encoded


def build_web_gallery(config: AppConfig) -> dict[str, Any]:
    engine = create_db_engine(config.database.path)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        service = StudentService(session, config.database.photos_dir)
        enrolled = service.list_enrolled_faces(model_name=MODEL_NAME)
    selected = select_kiosk_gallery(
        [
            GalleryEntry(
                student_id=item.student_id,
                full_name=item.full_name,
                embedding=item.embedding,
                program=item.program,
                group_name=item.group_name,
            )
            for item in enrolled
        ]
    )
    students: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in selected:
        if item.student_id in seen:
            continue
        photo = thumbnail_data_url(config.database.photos_dir / f"{item.student_id}.jpg")
        if not photo:
            continue
        seen.add(item.student_id)
        students.append(
            {
                "id": item.student_id,
                "name": item.full_name,
                "program": item.program or "",
                "group": item.group_name or "",
                "photo": photo,
            }
        )
    return {
        "code": config.kiosk.web_class_code,
        "students": students,
    }


def write_runtime_gallery(payload: dict[str, Any]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_FILE.write_text(json.dumps(payload), encoding="utf-8")
    return RUNTIME_FILE


def _gallery_post_url(config: AppConfig) -> str:
    base = config.kiosk.web_public_url.rstrip("/")
    return f"{base}/.netlify/functions/gallery"


def publish_web_gallery(config: AppConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    payload = build_web_gallery(config)
    path = write_runtime_gallery(payload)
    uploaded = False
    error = ""
    if config.kiosk.web_public_url:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            _gallery_post_url(config),
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                uploaded = 200 <= int(response.status) < 300
                if not uploaded:
                    error = f"HTTP {response.status}"
        except urllib.error.HTTPError as exc:
            error = f"HTTP {exc.code}"
            logger.warning("Netlify rechazó la galería: %s", exc)
        except urllib.error.URLError as exc:
            error = str(exc.reason or exc)
            logger.warning("No se alcanzó Netlify para la galería: %s", exc)
    count = len(payload["students"])
    if uploaded:
        message = f"Se enviaron {count} foto(s) al celular."
    elif error:
        message = f"Guardadas {count} foto(s) en este PC. El celular aún no las tiene ({error})."
    else:
        message = f"Guardadas {count} foto(s) en este PC."
    logger.info("%s Archivo=%s", message, path)
    return {
        "ok": True,
        "count": count,
        "uploaded": uploaded,
        "message": message,
        "path": str(path),
    }


def main() -> None:
    result = publish_web_gallery()
    print(result["message"])


if __name__ == "__main__":
    main()
