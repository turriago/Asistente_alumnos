"""Sube fotos y vídeos locales a Supabase Storage. Postgres solo guarda metadatos."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote

from attendance_system.config import PROJECT_ROOT, load_config
from attendance_system.gallery_sync import CARDS_FILE, RUNTIME_DIR, build_web_gallery, publish_web_gallery
from attendance_system.logging_setup import get_logger
from attendance_system.media_prepare import card_jpeg_from_sources, encode_jpeg, read_bgr
from attendance_system.students.inbox import find_principal_photo, list_photos, list_videos, ordered_enroll_photos, scan_inbox

logger = get_logger("supabase_sync")

BUCKET = "student-media"
MAX_VIDEO_BYTES = 40 * 1024 * 1024
PUBLIC_JS = PROJECT_ROOT / "web" / "js" / "supabase-public.js"


def load_env_file(path: Path | None = None) -> None:
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _settings() -> tuple[str, str, str]:
    load_env_file()
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
        or ""
    ).strip()
    anon = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or ""
    ).strip()
    if not url or not service:
        raise SystemExit(
            "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el archivo .env"
        )
    return url, service, anon


def _request(
    url: str,
    *,
    method: str,
    token: str,
    data: bytes | None = None,
    content_type: str = "application/json",
    extra_headers: dict[str, str] | None = None,
    timeout: int = 120,
) -> bytes:
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": token,
        "Content-Type": content_type,
    }
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase {exc.code} {url}: {detail}") from exc


def _public_url(base: str, path: str) -> str:
    return f"{base}/storage/v1/object/public/{BUCKET}/{quote(path)}"


def upload_bytes(base: str, token: str, path: str, payload: bytes, mime: str) -> str:
    encoded = quote(path)
    _request(
        f"{base}/storage/v1/object/{BUCKET}/{encoded}",
        method="POST",
        token=token,
        data=payload,
        content_type=mime,
        extra_headers={"x-upsert": "true"},
    )
    return _public_url(base, path)


def upsert_student(base: str, token: str, student: dict[str, str]) -> None:
    body = json.dumps(
        {
            "student_id": student["id"],
            "full_name": student["name"],
            "program": student.get("program") or "",
            "group_name": student.get("group") or "",
        }
    ).encode("utf-8")
    _request(
        f"{base}/rest/v1/students",
        method="POST",
        token=token,
        data=body,
        extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
    )


def replace_media(base: str, token: str, student_id: str, rows: list[dict[str, Any]]) -> None:
    _request(
        f"{base}/rest/v1/student_media?student_id=eq.{quote(student_id)}",
        method="DELETE",
        token=token,
        extra_headers={"Prefer": "return=minimal"},
    )
    if not rows:
        return
    _request(
        f"{base}/rest/v1/student_media",
        method="POST",
        token=token,
        data=json.dumps(rows).encode("utf-8"),
        extra_headers={"Prefer": "return=minimal"},
    )


def write_public_js(url: str, anon: str) -> None:
    if not anon:
        logger.warning("Sin SUPABASE_ANON_KEY: el celular no leerá la API REST directa.")
        return
    PUBLIC_JS.write_text(
        "export const SUPABASE_URL = "
        + json.dumps(url)
        + ";\nexport const SUPABASE_ANON_KEY = "
        + json.dumps(anon)
        + ";\n",
        encoding="utf-8",
    )


def _inbox_by_name(inbox_dir: Path) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for person in scan_inbox(inbox_dir):
        mapped[person.full_name.casefold()] = person
        if person.student_id:
            mapped[person.student_id.casefold()] = person
    return mapped


def sync() -> dict[str, Any]:
    base, service, anon = _settings()
    config = load_config()
    gallery = build_web_gallery(config)
    inbox_map = _inbox_by_name(config.database.inbox_dir)
    card_urls: dict[str, str] = {}
    uploaded = 0

    for student in gallery["students"]:
        person = inbox_map.get(student["id"].casefold()) or inbox_map.get(student["name"].casefold())
        photos: list[Path] = []
        videos: list[Path] = []
        if person is not None:
            principal = find_principal_photo(person.folder)
            photos = list(ordered_enroll_photos(list_photos(person.folder), principal))
            videos = list(list_videos(person.folder))
        fallback = config.database.photos_dir / f"{student['id']}.jpg"
        card = card_jpeg_from_sources(photos, videos, fallback if fallback.is_file() else None)
        if card is None:
            logger.warning("Sin imagen de ficha para %s", student["id"])
            continue

        upsert_student(base, service, student)
        media_rows: list[dict[str, Any]] = []
        card_path = f"{student['id']}/card.jpg"
        card_url = upload_bytes(base, service, card_path, card, "image/jpeg")
        card_urls[student["id"]] = card_url
        media_rows.append(
            {
                "student_id": student["id"],
                "kind": "card",
                "bucket_path": card_path,
                "public_url": card_url,
                "mime": "image/jpeg",
                "byte_size": len(card),
                "is_card": True,
            }
        )
        uploaded += 1

        for index, photo in enumerate(photos, start=1):
            image = read_bgr(photo)
            if image is None:
                continue
            encoded = encode_jpeg(image, max_side=1600, quality=85)
            if encoded is None:
                continue
            rel = f"{student['id']}/photo_{index:02d}.jpg"
            url = upload_bytes(base, service, rel, encoded, "image/jpeg")
            media_rows.append(
                {
                    "student_id": student["id"],
                    "kind": "photo",
                    "bucket_path": rel,
                    "public_url": url,
                    "mime": "image/jpeg",
                    "byte_size": len(encoded),
                    "is_card": False,
                }
            )
            uploaded += 1

        for video in videos:
            size = video.stat().st_size
            if size > MAX_VIDEO_BYTES:
                logger.warning("Vídeo demasiado grande (%s, %s bytes)", video.name, size)
                continue
            payload = video.read_bytes()
            suffix = video.suffix.lower().lstrip(".") or "mp4"
            mime = "video/quicktime" if suffix == "mov" else f"video/{suffix}"
            rel = f"{student['id']}/video_{video.stem}.{suffix}"
            url = upload_bytes(base, service, rel, payload, mime)
            media_rows.append(
                {
                    "student_id": student["id"],
                    "kind": "video",
                    "bucket_path": rel,
                    "public_url": url,
                    "mime": mime,
                    "byte_size": size,
                    "is_card": False,
                }
            )
            uploaded += 1

        replace_media(base, service, student["id"], media_rows)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    CARDS_FILE.write_text(json.dumps(card_urls), encoding="utf-8")
    write_public_js(base, anon)
    published = publish_web_gallery(config)
    return {
        "ok": True,
        "files": uploaded,
        "students": len(card_urls),
        "message": (
            f"Supabase: {len(card_urls)} estudiante(s), {uploaded} archivo(s). "
            + str(published.get("message") or "")
        ),
    }


def main() -> None:
    result = sync()
    print(result["message"])


if __name__ == "__main__":
    main()
