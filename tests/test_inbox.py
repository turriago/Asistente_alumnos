from __future__ import annotations

from pathlib import Path

from attendance_system.students.inbox import parse_folder_label, read_name_file, scan_inbox, split_full_name


def test_split_full_name() -> None:
    assert split_full_name("Ana Pérez Demo") == ("Ana", "Pérez Demo")
    assert split_full_name("Solo") == ("Solo", "Sin apellido")


def test_parse_folder_with_and_without_id() -> None:
    student_id, name = parse_folder_label("20260001 Ana Pérez Demo")
    assert student_id == "20260001"
    assert name == "Ana Pérez Demo"
    student_id, name = parse_folder_label("Nombre Apellido")
    assert student_id is None
    assert name == "Nombre Apellido"


def test_slot_folder_uses_nombre_txt(tmp_path: Path) -> None:
    slot = tmp_path / "persona_01"
    slot.mkdir()
    (slot / "nombre.txt").write_text("# comentario\nEscribe el nombre completo aquí\n", encoding="utf-8")
    assert read_name_file(slot) is None
    assert scan_inbox(tmp_path) == []
    (slot / "nombre.txt").write_text("Ana Pérez Demo\n", encoding="utf-8")
    (slot / "2.jpg").write_bytes(b"x")
    (slot / "1_foto.jpg").write_bytes(b"y")
    people = scan_inbox(tmp_path)
    assert len(people) == 1
    assert people[0].full_name == "Ana Pérez Demo"
    assert people[0].student_id is None
    from attendance_system.students.inbox import find_principal_photo, ordered_enroll_photos

    principal = find_principal_photo(slot)
    assert principal is not None
    assert principal.name == "1_foto.jpg"
    ordered = ordered_enroll_photos(people[0].photos, principal)
    assert ordered[0].name == "1_foto.jpg"


def test_name_from_any_txt_and_1_prefix_beats_principal_stem(tmp_path: Path) -> None:
    slot = tmp_path / "persona_02"
    slot.mkdir()
    (slot / "anuar.txt").write_text("vizcaino perez anuar\n", encoding="utf-8")
    (slot / "photo_principal.jpeg").write_bytes(b"old")
    (slot / "1_IMG_1534.JPG").write_bytes(b"card")
    (slot / "IMG_1536.JPG").write_bytes(b"side")
    people = scan_inbox(tmp_path)
    assert people[0].full_name == "vizcaino perez anuar"
    from attendance_system.students.inbox import find_principal_photo, ordered_enroll_photos

    principal = find_principal_photo(slot)
    assert principal is not None
    assert principal.name == "1_IMG_1534.JPG"
    ordered = ordered_enroll_photos(people[0].photos, principal)
    assert ordered[0].name == "1_IMG_1534.JPG"
