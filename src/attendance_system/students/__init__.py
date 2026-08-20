"""Estudiantes de prueba."""

from attendance_system.students.service import (
    DuplicateStudentError,
    StudentError,
    StudentNotFoundError,
    StudentRecord,
    StudentService,
)

__all__ = [
    "DuplicateStudentError",
    "StudentError",
    "StudentNotFoundError",
    "StudentRecord",
    "StudentService",
]
