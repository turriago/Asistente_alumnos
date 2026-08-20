"""Carga estudiantes ficticios desde CSV de sample. No pisa embeddings ya enrolados."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import NoReturn

from attendance_system.config import PROJECT_ROOT, load_config
from attendance_system.database.session import create_db_engine, make_session_factory, session_scope
from attendance_system.logging_setup import setup_logging
from attendance_system.students.service import DuplicateStudentError, StudentService

SAMPLE_CSV = PROJECT_ROOT / "data" / "sample" / "students.sample.csv"


def seed_students(csv_path: Path | None = None) -> int:
    config = load_config()
    setup_logging(config.logging)
    path = csv_path or SAMPLE_CSV
    if not path.exists():
        raise FileNotFoundError(path)

    engine = create_db_engine(config.database.path)
    factory = make_session_factory(engine)
    created = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with session_scope(factory) as session:
        service = StudentService(session, config.database.photos_dir)
        for raw in rows:
            student_id = (raw.get("student_id") or "").strip()
            try:
                service.create(
                    student_id=student_id,
                    first_name=(raw.get("first_name") or "").strip(),
                    last_name=(raw.get("last_name") or "").strip(),
                    program=(raw.get("program") or "").strip(),
                    group_name=(raw.get("group") or raw.get("group_name") or "").strip(),
                )
                created += 1
            except DuplicateStudentError:
                continue
    return created


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Crea estudiantes de demo ficticios.")
    parser.parse_args()
    count = seed_students()
    print(f"Estudiantes de demo creados o ya existentes. Nuevos: {count}.")
    config = load_config()
    engine = create_db_engine(config.database.path)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        service = StudentService(session, config.database.photos_dir)
        print("ID | Nombre | Programa | Grupo | Rostro")
        for row in service.list_all():
            face = "sí" if row.has_face else "no"
            print(f"{row.student_id} | {row.full_name} | {row.program} | {row.group_name} | {face}")
    print("Datos ficticios. No uses listas reales en Git.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
