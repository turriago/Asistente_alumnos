"""Carpeta donde se dejan fotos de enrolamiento. No es data/photos/ (miniaturas)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
NAME_FILE = "nombre.txt"
PRINCIPAL_STEMS = {"photo_principal", "foto_principal", "principal"}
PRINCIPAL_PREFIX = re.compile(r"^1_", re.IGNORECASE)
SLOT_FOLDER = re.compile(r"^persona_\d+$", re.IGNORECASE)
_ID_PREFIX = re.compile(
    r"^(?P<student_id>\d{4,32}|TMP-\d{4})(?:\s+|__)(?P<name>.+)$",
    re.IGNORECASE,
)
_PLACEHOLDERS = {
    "",
    "pendiente",
    "escribe el nombre completo aqui",
    "escribe el nombre completo aquí",
    "nombre completo",
}


@dataclass(frozen=True)
class InboxPerson:
    folder: Path
    student_id: str | None
    full_name: str
    photos: tuple[Path, ...]


def split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        raise ValueError("El nombre no puede estar vacío.")
    if len(parts) == 1:
        return parts[0], "Sin apellido"
    return parts[0], " ".join(parts[1:])


def parse_folder_label(folder_name: str) -> tuple[str | None, str]:
    label = folder_name.strip().replace("_", " ")
    match = _ID_PREFIX.match(label)
    if match:
        return match.group("student_id").strip(), match.group("name").strip()
    return None, label


def _name_from_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.casefold() in _PLACEHOLDERS:
            continue
        return line
    return None


def read_name_file(folder: Path) -> str | None:
    name = _name_from_text(folder / NAME_FILE)
    if name:
        return name
    extras = sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".txt"
        and path.name.lower() != NAME_FILE
    )
    for path in extras:
        name = _name_from_text(path)
        if name:
            return name
    return None


def list_videos(folder: Path) -> tuple[Path, ...]:
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    ]
    return tuple(sorted(files, key=lambda item: item.name.lower()))


def list_photos(folder: Path) -> tuple[Path, ...]:
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    return tuple(sorted(files, key=lambda item: item.name.lower()))


def is_principal_photo(path: Path) -> bool:
    if PRINCIPAL_PREFIX.match(path.name):
        return True
    return path.stem.lower() in PRINCIPAL_STEMS


def find_principal_photo(folder: Path) -> Path | None:
    photos = list_photos(folder)
    prefixed = [path for path in photos if PRINCIPAL_PREFIX.match(path.name)]
    if prefixed:
        return prefixed[0]
    for path in photos:
        if path.stem.lower() in PRINCIPAL_STEMS:
            return path
    return None


def ordered_enroll_photos(photos: tuple[Path, ...], principal: Path | None) -> tuple[Path, ...]:
    if principal is None or principal not in photos:
        return photos
    rest = [path for path in photos if path != principal]
    return (principal, *rest)


def scan_inbox(inbox_dir: Path) -> list[InboxPerson]:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    people: list[InboxPerson] = []
    for folder in sorted(inbox_dir.iterdir(), key=lambda item: item.name.lower()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        student_id, folder_name = parse_folder_label(folder.name)
        file_name = read_name_file(folder)
        if file_name:
            full_name = file_name
        elif SLOT_FOLDER.match(folder.name):
            continue
        else:
            full_name = folder_name
        if not full_name:
            continue
        people.append(
            InboxPerson(
                folder=folder,
                student_id=student_id,
                full_name=full_name,
                photos=list_photos(folder),
            )
        )
    return people
