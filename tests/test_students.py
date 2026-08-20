from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from attendance_system.database.session import create_db_engine, make_session_factory, session_scope
from attendance_system.face.types import DetectedFace
from attendance_system.students.seed import seed_students
from attendance_system.students.service import (
    DuplicateStudentError,
    StudentNotFoundError,
    StudentService,
)


def _face() -> DetectedFace:
    return DetectedFace(
        x=10,
        y=10,
        width=80,
        height=90,
        score=0.9,
        landmarks=((20, 20), (70, 20), (45, 50), (25, 80), (65, 80)),
    )


def test_create_and_reject_duplicate(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "t.db")
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        service = StudentService(session, tmp_path / "photos")
        created = service.create(
            student_id="20260001",
            first_name="Ana",
            last_name="Pérez Demo",
            program="Sistemas",
            group_name="A",
        )
        assert created.full_name == "Ana Pérez Demo"
        assert created.has_face is False
        with pytest.raises(DuplicateStudentError):
            service.create(
                student_id="20260001",
                first_name="Otra",
                last_name="Persona",
                program="Sistemas",
                group_name="A",
            )


def test_delete_removes_student_and_thumbnail(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "t.db")
    factory = make_session_factory(engine)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    frame[10:100, 10:90] = 180
    with session_scope(factory) as session:
        service = StudentService(session, tmp_path / "photos")
        service.create(
            student_id="20260001",
            first_name="Ana",
            last_name="Pérez Demo",
            program="Sistemas",
            group_name="A",
        )
        service.enroll_face(
            "20260001",
            frame,
            _face(),
            np.array([1.0, 0.0], dtype=np.float32),
            model_name="test-model",
        )
        assert (tmp_path / "photos" / "20260001.jpg").exists()
        service.delete("20260001")
        assert service.get("20260001") is None
        assert not (tmp_path / "photos" / "20260001.jpg").exists()
        with pytest.raises(StudentNotFoundError):
            service.delete("20260001")


def test_enroll_stores_normalized_embedding_not_full_photo(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "t.db")
    factory = make_session_factory(engine)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    frame[10:100, 10:90] = 180
    embedding = np.array([3.0, 4.0], dtype=np.float32)
    with session_scope(factory) as session:
        service = StudentService(session, tmp_path / "photos")
        service.create(
            student_id="20260001",
            first_name="Ana",
            last_name="Pérez Demo",
            program="Sistemas",
            group_name="A",
        )
        record = service.enroll_face(
            "20260001",
            frame,
            _face(),
            embedding,
            model_name="test-model",
        )
        stored = service.get_embedding("20260001")
        assert record.has_face is True
        assert stored is not None
        assert stored.shape == (2,)
        np.testing.assert_allclose(np.linalg.norm(stored), 1.0, atol=1e-5)
        assert (tmp_path / "photos" / "20260001.jpg").exists()
        gallery = service.list_enrolled_faces(model_name="test-model")
        assert len(gallery) == 1
        assert gallery[0].student_id == "20260001"
        skipped = service.list_enrolled_faces(model_name="sface_2021dec")
        assert skipped == []
        cleared = service.clear_face("20260001")
        assert cleared.has_face is False
        assert service.get_embedding("20260001") is None
        assert service.list_enrolled_faces(model_name="test-model") == []


def test_enroll_three_poses_expands_gallery(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "t.db")
    factory = make_session_factory(engine)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    frame[10:100, 10:90] = 180
    with session_scope(factory) as session:
        service = StudentService(session, tmp_path / "photos")
        service.create(
            student_id="20260001",
            first_name="Ana",
            last_name="Pérez Demo",
            program="Sistemas",
            group_name="A",
        )
        service.enroll_faces(
            "20260001",
            [
                (frame, _face(), np.array([1.0, 0.0], dtype=np.float32)),
                (frame, _face(), np.array([0.2, 1.0], dtype=np.float32)),
                (frame, _face(), np.array([0.9, 0.1], dtype=np.float32)),
            ],
            model_name="test-model",
        )
        gallery = service.list_enrolled_faces(model_name="test-model")
        assert len(gallery) == 3
        assert {item.student_id for item in gallery} == {"20260001"}


def test_enroll_unknown_student(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "t.db")
    factory = make_session_factory(engine)
    frame = np.zeros((120, 120, 3), dtype=np.uint8)
    with session_scope(factory) as session:
        service = StudentService(session, tmp_path / "photos")
        with pytest.raises(StudentNotFoundError):
            service.enroll_face("nope", frame, _face(), np.ones(4, dtype=np.float32), model_name="x")


def test_seed_sample_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from attendance_system.config import DatabaseSettings, load_config

    config = load_config()
    monkeypatch.setattr(
        "attendance_system.students.seed.load_config",
        lambda: type(config)(
            demo_mode=True,
            camera=config.camera,
            logging=config.logging,
            face=config.face,
            hands=config.hands,
            challenge=config.challenge,
            database=DatabaseSettings(
                path=tmp_path / "demo.db",
                photos_dir=tmp_path / "photos",
                inbox_dir=tmp_path / "inbox",
            ),
            kiosk=config.kiosk,
            config_path=config.config_path,
        ),
    )
    created = seed_students()
    assert created == 5
    created_again = seed_students()
    assert created_again == 0


def test_temp_id_and_find_by_name(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "t.db")
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        service = StudentService(session, tmp_path / "photos")
        assert service.next_temp_id() == "TMP-0001"
        service.create(
            student_id="TMP-0001",
            first_name="Ana",
            last_name="Pérez Demo",
            program="Pendiente",
            group_name="N/A",
        )
        assert service.next_temp_id() == "TMP-0002"
        found = service.find_by_full_name("Ana  Pérez Demo")
        assert found is not None
        assert found.student_id == "TMP-0001"
