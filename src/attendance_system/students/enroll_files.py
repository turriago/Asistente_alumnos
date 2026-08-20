"""Enrolar desde fotos en data/enroll_inbox/. No usa la webcam."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

import cv2
import numpy as np

from attendance_system.config import PROJECT_ROOT, load_config
from attendance_system.database.session import create_db_engine, make_session_factory, session_scope
from attendance_system.face.detector import FaceDetector, FaceDetectorError
from attendance_system.face.embedder import EmbedderError, FaceEmbedder
from attendance_system.face.model import FaceModelError
from attendance_system.face.types import DetectedFace
from attendance_system.logging_setup import setup_logging
from attendance_system.students.inbox import (
    InboxPerson,
    find_principal_photo,
    ordered_enroll_photos,
    scan_inbox,
    split_full_name,
)
from attendance_system.students.service import DuplicateStudentError, StudentService

PROGRAM_PENDING = "Pendiente de lista"
GROUP_PENDING = "N/A"


def read_bgr(path) -> np.ndarray:
    raw = np.fromfile(str(path), dtype=np.uint8)
    frame = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if frame is None:
        raise EmbedderError(f"No se pudo leer la imagen: {path}")
    return frame


MIN_PHOTOS = 1


def enroll_person(person: InboxPerson, *, needed: int) -> str:
    config = load_config()
    if len(person.photos) < MIN_PHOTOS:
        raise EmbedderError(
            f"{person.folder.name}: hay {len(person.photos)} foto(s); se necesita al menos {MIN_PHOTOS}."
        )

    detector = FaceDetector(config.face)
    embedder = FaceEmbedder(PROJECT_ROOT / "models")
    photos = ordered_enroll_photos(person.photos, find_principal_photo(person.folder))
    shots: list[tuple[np.ndarray, DetectedFace, np.ndarray]] = []
    for photo in photos[:needed]:
        frame = read_bgr(photo)
        faces = detector.detect(frame)
        if not faces:
            raise EmbedderError(f"{photo.name}: no se detectó ningún rostro.")
        if len(faces) > 1:
            print(
                f"ℹ️  {photo.name}: {len(faces)} rostros; se usa el más grande (primer plano)."
            )
        shots.append((frame, faces[0], embedder.embed(frame, faces[0])))

    engine = create_db_engine(config.database.path)
    factory = make_session_factory(engine)
    first_name, last_name = split_full_name(person.full_name)
    with session_scope(factory) as session:
        service = StudentService(session, config.database.photos_dir)
        existing = None
        if person.student_id:
            existing = service.get(person.student_id)
        if existing is None:
            existing = service.find_by_full_name(person.full_name)
        if existing is None:
            student_id = person.student_id or service.next_temp_id()
            try:
                service.create(
                    student_id=student_id,
                    first_name=first_name,
                    last_name=last_name,
                    program=PROGRAM_PENDING,
                    group_name=GROUP_PENDING,
                )
            except DuplicateStudentError:
                student_id = service.next_temp_id()
                service.create(
                    student_id=student_id,
                    first_name=first_name,
                    last_name=last_name,
                    program=PROGRAM_PENDING,
                    group_name=GROUP_PENDING,
                )
        else:
            student_id = existing.student_id
        record = service.enroll_faces(student_id, shots, model_name=embedder.model_name)
    return f"{record.student_id} | {record.full_name} | {needed} tomas"


def run_inbox() -> int:
    config = load_config()
    setup_logging(config.logging)
    inbox = config.database.inbox_dir
    inbox.mkdir(parents=True, exist_ok=True)
    people = scan_inbox(inbox)
    recommended = len(config.face.enroll_poses)
    ready = [person for person in people if len(person.photos) >= MIN_PHOTOS]
    pending = [person for person in people if len(person.photos) < MIN_PHOTOS]
    if not ready:
        print(f"Nadie está listo todavía en {inbox}")
        print("En cada carpeta persona_01, persona_02, ... :")
        print("  1. Nombre completo en nombre.txt o en un .txt (Giovanny.txt, anuar.txt).")
        print(f"  2. Copia al menos 1 foto (mejor {recommended}: frente, izquierda, derecha).")
        print("  3. La foto de la ficha es la que empieza por 1_.")
        print("Luego: python -m attendance_system.students.enroll_files")
        return 1

    errors = 0
    for person in pending:
        print(
            f"⏳ {person.folder.name} ({person.full_name}): faltan fotos "
            f"({len(person.photos)}/{MIN_PHOTOS})."
        )
    for person in ready:
        try:
            take = min(len(person.photos), recommended)
            if take < recommended:
                print(
                    f"ℹ️  {person.folder.name}: {take} foto(s); lo ideal son {recommended}."
                )
            line = enroll_person(person, needed=take)
            principal = find_principal_photo(person.folder)
            extra = f" | foto principal={principal.name}" if principal else ""
            print(f"✅ {line}{extra}")
        except (EmbedderError, FaceModelError, FaceDetectorError, ValueError) as exc:
            errors += 1
            print(f"⚠️  {person.folder.name}: {exc}", file=sys.stderr)
    return 1 if errors else 0


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Enrolar personas desde data/enroll_inbox/.")
    parser.parse_args()
    raise SystemExit(run_inbox())


if __name__ == "__main__":
    main()
