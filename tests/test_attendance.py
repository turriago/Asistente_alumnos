from datetime import datetime

from attendance_system.attendance import (
    UNIVERSITY_HEADERS,
    colombia_today,
    day_summary_rows,
    missing_rows,
    present_rows,
    split_roster,
    university_template_rows,
)


def test_split_roster_separates_present_and_missing() -> None:
    students = [
        {"student_id": "TMP-0002", "full_name": "vizcaino perez anuar"},
        {"student_id": "TMP-0001", "full_name": "Giovanny Andres Batista Sierra"},
        {"student_id": "TMP-0004", "full_name": "Luis David Turriago Serrano"},
    ]
    present, missing = split_roster(
        students,
        [
            {"student_id": "TMP-0004", "passed_at": "2026-08-20T03:01:00+00:00", "source": "web"},
            {"student_id": "TMP-0001", "passed_at": "2026-08-20T03:00:00+00:00", "source": "kiosk"},
        ],
    )
    assert [row["student_id"] for row in present] == ["TMP-0001", "TMP-0004"]
    assert present[0]["source"] == "kiosk"
    assert [row["student_id"] for row in missing] == ["TMP-0002"]


def test_split_roster_keeps_first_pass_and_sorts_pending() -> None:
    students = [
        {"id": "B", "name": "zeta"},
        {"id": "A", "name": "ana"},
    ]
    present, missing = split_roster(students, [{"id": "B", "passed_at": "1"}])
    assert [row["id"] for row in present] == ["B"]
    assert [row["id"] for row in missing] == ["A"]


def test_empty_class_is_all_missing() -> None:
    present, missing = split_roster([{"student_id": "TMP-0003", "full_name": "santiago"}], [])
    assert present == []
    assert len(missing) == 1


def test_colombia_today_is_iso_date() -> None:
    day = colombia_today(datetime(2026, 8, 20, 23, 30))
    assert day == "2026-08-20"


def test_day_excel_has_date_time_and_counts() -> None:
    present = [
        {
            "student_id": "TMP-0004",
            "full_name": "Luis",
            "passed_at": "2026-08-20T05:10:00+00:00",
            "source": "web",
        }
    ]
    missing = [
        {"student_id": "TMP-0001", "full_name": "Giovanny", "program": "Sistemas", "group_name": "A"}
    ]
    summary = dict(
        day_summary_rows(
            {
                "class_code": "aula1",
                "session_date": "2026-08-20",
                "started_at": "2026-08-20T05:00:00+00:00",
            },
            present,
            missing,
        )
    )
    assert summary["Fecha"] == "2026-08-20"
    assert summary["Hora de activación del QR"] == "00:00:00"
    assert summary["Personas presentes"] == "1"
    assert summary["Personas que faltaron"] == "1"
    assert present_rows(present)[1][0] == "TMP-0004"
    assert missing_rows(missing)[1][0] == "TMP-0001"


def test_university_template_keeps_official_headers() -> None:
    rows = university_template_rows(
        [{"student_id": "TMP-0004", "full_name": "Luis David", "program": "Sistemas"}]
    )
    assert rows[0] == UNIVERSITY_HEADERS
    assert rows[1][0] == "TMP-0004"
    assert rows[1][3] == ""
