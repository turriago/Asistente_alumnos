"""Errores y operaciones de estudiantes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from attendance_system.database.models import Student
from attendance_system.face.templates import pack_embeddings, unpack_embeddings
from attendance_system.face.types import DetectedFace
from attendance_system.logging_setup import get_logger

logger = get_logger("students")


class StudentError(Exception):
    """Error de registro de estudiantes."""


class DuplicateStudentError(StudentError):
    """El ID ya existe."""


class StudentNotFoundError(StudentError):
    """No hay estudiante con ese ID."""


@dataclass(frozen=True)
class EnrolledFace:
    student_id: str
    full_name: str
    program: str
    group_name: str
    embedding: np.ndarray
    embedding_model: str
    thumbnail_path: str | None


@dataclass(frozen=True)
class StudentRecord:
    student_id: str
    first_name: str
    last_name: str
    full_name: str
    program: str
    group_name: str
    has_face: bool
    thumbnail_path: str | None
    embedding_model: str | None


def _to_record(row: Student) -> StudentRecord:
    return StudentRecord(
        student_id=row.student_id,
        first_name=row.first_name,
        last_name=row.last_name,
        full_name=row.full_name,
        program=row.program,
        group_name=row.group_name,
        has_face=row.has_face,
        thumbnail_path=row.thumbnail_path,
        embedding_model=row.embedding_model,
    )


class StudentService:
    def __init__(self, session: Session, photos_dir: Path) -> None:
        self.session = session
        self.photos_dir = photos_dir
        self.photos_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        student_id: str,
        first_name: str,
        last_name: str,
        program: str,
        group_name: str,
    ) -> StudentRecord:
        student_id = student_id.strip()
        if not student_id:
            raise StudentError("El ID es obligatorio.")
        if self.get(student_id) is not None:
            raise DuplicateStudentError(f"Ya existe un estudiante con ID {student_id}.")
        first_name = first_name.strip()
        last_name = last_name.strip()
        if not first_name or not last_name:
            raise StudentError("Nombre y apellido son obligatorios.")
        row = Student(
            student_id=student_id,
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}".strip(),
            program=program.strip() or "Sin programa",
            group_name=group_name.strip() or "N/A",
        )
        self.session.add(row)
        self.session.flush()
        logger.info("Estudiante registrado: %s (%s).", row.student_id, row.full_name)
        return _to_record(row)

    def delete(self, student_id: str) -> None:
        row = self._row(student_id)
        if row is None:
            raise StudentNotFoundError(f"No existe el estudiante {student_id}.")
        photo = self.photos_dir / f"{student_id}.jpg"
        self.session.delete(row)
        self.session.flush()
        if photo.is_file():
            photo.unlink()
        logger.info("Estudiante eliminado: %s.", student_id)

    def get(self, student_id: str) -> StudentRecord | None:
        row = self._row(student_id)
        return _to_record(row) if row else None

    def require(self, student_id: str) -> StudentRecord:
        record = self.get(student_id)
        if record is None:
            raise StudentNotFoundError(f"No existe el estudiante {student_id}.")
        return record

    def list_all(self) -> list[StudentRecord]:
        rows = self.session.scalars(select(Student).order_by(Student.student_id)).all()
        return [_to_record(row) for row in rows]

    def find_by_full_name(self, full_name: str) -> StudentRecord | None:
        needle = " ".join(full_name.strip().split())
        if not needle:
            return None
        rows = self.session.scalars(select(Student)).all()
        for row in rows:
            if " ".join(row.full_name.split()).casefold() == needle.casefold():
                return _to_record(row)
        return None

    def next_temp_id(self) -> str:
        used = {row.student_id for row in self.list_all()}
        index = 1
        while f"TMP-{index:04d}" in used:
            index += 1
        return f"TMP-{index:04d}"

    def set_thumbnail(self, student_id: str, crop: np.ndarray) -> Path:
        row = self._row(student_id)
        if row is None:
            raise StudentNotFoundError(f"No existe el estudiante {student_id}.")
        path = _save_thumbnail(self.photos_dir, student_id, crop)
        row.thumbnail_path = str(path)
        self.session.flush()
        logger.info("Miniatura actualizada para %s.", student_id)
        return path

    def enroll_face(
        self,
        student_id: str,
        frame: np.ndarray,
        face: DetectedFace,
        embedding: np.ndarray,
        *,
        model_name: str,
    ) -> StudentRecord:
        if embedding.ndim != 1:
            raise StudentError("El embedding debe ser un vector 1-D.")
        row = self._row(student_id)
        if row is None:
            raise StudentNotFoundError(f"No existe el estudiante {student_id}.")
        vector = np.asarray(embedding, dtype=np.float32)
        return self.enroll_faces(
            student_id,
            [(frame, face, vector)],
            model_name=model_name,
        )

    def enroll_faces(
        self,
        student_id: str,
        shots: list[tuple[np.ndarray, DetectedFace, np.ndarray]],
        *,
        model_name: str,
    ) -> StudentRecord:
        if not shots:
            raise StudentError("Hace falta al menos una toma.")
        row = self._row(student_id)
        if row is None:
            raise StudentNotFoundError(f"No existe el estudiante {student_id}.")
        vectors = [np.asarray(embedding, dtype=np.float32) for _frame, _face, embedding in shots]
        blob, dim = pack_embeddings(vectors)
        thumbnail = _save_thumbnail(
            self.photos_dir,
            student_id,
            shots[0][1].crop(shots[0][0], pad=0.45),
        )
        row.embedding = blob
        row.embedding_dim = dim
        row.embedding_model = model_name
        row.thumbnail_path = str(thumbnail)
        self.session.flush()
        logger.info(
            "Rostro enrolado para %s. Modelo=%s dim=%s tomas=%s. No se guarda la foto original.",
            student_id,
            model_name,
            dim,
            len(shots),
        )
        return _to_record(row)

    def clear_face(self, student_id: str) -> StudentRecord:
        row = self._row(student_id)
        if row is None:
            raise StudentNotFoundError(f"No existe el estudiante {student_id}.")
        row.embedding = None
        row.embedding_dim = None
        row.embedding_model = None
        self.session.flush()
        logger.info("Embedding eliminado para %s. El registro del estudiante se mantiene.", student_id)
        return _to_record(row)

    def list_enrolled_faces(self, *, model_name: str) -> list[EnrolledFace]:
        rows = self.session.scalars(select(Student).order_by(Student.student_id)).all()
        enrolled: list[EnrolledFace] = []
        for row in rows:
            if row.embedding is None or row.embedding_dim is None:
                continue
            if row.embedding_model != model_name:
                logger.warning(
                    "Omitiendo embedding de %s: modelo %s distinto de %s.",
                    row.student_id,
                    row.embedding_model,
                    model_name,
                )
                continue
            try:
                vectors = unpack_embeddings(row.embedding, row.embedding_dim)
            except ValueError as exc:
                logger.warning("No se pudieron leer embeddings de %s: %s", row.student_id, exc)
                continue
            for vector in vectors:
                enrolled.append(
                    EnrolledFace(
                        student_id=row.student_id,
                        full_name=row.full_name,
                        program=row.program,
                        group_name=row.group_name,
                        embedding=vector,
                        embedding_model=row.embedding_model or model_name,
                        thumbnail_path=row.thumbnail_path,
                    )
                )
        return enrolled

    def get_embedding(self, student_id: str) -> np.ndarray | None:
        row = self._row(student_id)
        if row is None or row.embedding is None or row.embedding_dim is None:
            return None
        vectors = unpack_embeddings(row.embedding, row.embedding_dim)
        return vectors[0] if vectors else None

    def _row(self, student_id: str) -> Student | None:
        return self.session.scalar(select(Student).where(Student.student_id == student_id.strip()))


def _save_thumbnail(photos_dir: Path, student_id: str, crop: np.ndarray) -> Path:
    if crop.size == 0:
        raise StudentError("No se pudo recortar el rostro.")
    resized = cv2.resize(crop, (128, 128), interpolation=cv2.INTER_AREA)
    path = photos_dir / f"{student_id}.jpg"
    if not cv2.imwrite(str(path), resized):
        raise StudentError(f"No se pudo guardar la miniatura en {path}.")
    return path
