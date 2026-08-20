"""Marca de prueba exitosa. Una vez por estudiante y día de clase."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from attendance_system.config import AppConfig
from attendance_system.logging_setup import get_logger
from attendance_system.supabase_sync import load_env_file

logger = get_logger("attendance")

BOGOTA = ZoneInfo("America/Bogota")
UNIVERSITY_HEADERS = [
    "codigo_estudiante",
    "nombres",
    "apellidos",
    "documento",
    "programa",
    "grupo",
    "correo",
]


def colombia_today(now: datetime | None = None) -> str:
    stamp = now or datetime.now(BOGOTA)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=BOGOTA)
    return stamp.astimezone(BOGOTA).date().isoformat()


def format_colombia_time(iso: str | None) -> str:
    if not iso:
        return ""
    stamp = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(BOGOTA)
    return stamp.strftime("%H:%M:%S")


def split_roster(
    students: list[dict[str, Any]],
    passes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {str(row.get("student_id") or row.get("id")): row for row in passes}
    present: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for student in students:
        student_id = str(student.get("student_id") or student.get("id") or "")
        stamp = by_id.get(student_id)
        if stamp:
            present.append({**student, "passed_at": stamp.get("passed_at"), "source": stamp.get("source")})
        else:
            missing.append(student)
    present.sort(key=lambda item: str(item.get("passed_at") or ""))
    missing.sort(key=lambda item: str(item.get("full_name") or item.get("name") or "").casefold())
    return present, missing


def day_summary_rows(
    session: dict[str, Any],
    present: list[dict[str, Any]],
    missing: list[dict[str, Any]],
) -> list[list[str]]:
    total = len(present) + len(missing)
    return [
        ["Clase", str(session.get("class_code") or "")],
        ["Fecha", str(session.get("session_date") or "")],
        ["Hora de activación del QR", format_colombia_time(str(session.get("started_at") or ""))],
        ["Personas presentes", str(len(present))],
        ["Personas que faltaron", str(len(missing))],
        ["Total en lista", str(total)],
    ]


def present_rows(present: list[dict[str, Any]]) -> list[list[str]]:
    rows = [["ID", "Nombre", "Hora de la prueba", "Desde"]]
    for student in present:
        source = "kiosco" if student.get("source") == "kiosk" else "celular"
        rows.append(
            [
                str(student.get("student_id") or student.get("id") or ""),
                str(student.get("full_name") or student.get("name") or ""),
                format_colombia_time(str(student.get("passed_at") or "")),
                source,
            ]
        )
    return rows


def missing_rows(missing: list[dict[str, Any]]) -> list[list[str]]:
    rows = [["ID", "Nombre", "Programa", "Grupo"]]
    for student in missing:
        rows.append(
            [
                str(student.get("student_id") or student.get("id") or ""),
                str(student.get("full_name") or student.get("name") or ""),
                str(student.get("program") or ""),
                str(student.get("group_name") or student.get("group") or ""),
            ]
        )
    return rows


def university_template_rows(students: list[dict[str, Any]] | None = None) -> list[list[str]]:
    rows = [list(UNIVERSITY_HEADERS)]
    for student in students or []:
        name = str(student.get("full_name") or student.get("name") or "").strip()
        parts = name.split(" ", 1)
        rows.append(
            [
                str(student.get("student_id") or student.get("id") or ""),
                parts[0] if parts else "",
                parts[1] if len(parts) > 1 else "",
                "",
                str(student.get("program") or ""),
                str(student.get("group_name") or student.get("group") or ""),
                "",
            ]
        )
    if len(rows) == 1:
        rows.append(["", "", "", "", "", "", ""])
    return rows


def _creds() -> tuple[str, str]:
    load_env_file()
    base = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    token = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or ""
    ).strip()
    return base, token


def _request(
    base: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    query: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    prefer: str = "",
) -> Any:
    url = f"{base}/rest/v1/{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": token,
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        logger.warning(
            "Supabase %s HTTP %s: %s",
            path,
            exc.code,
            exc.read().decode("utf-8", errors="replace"),
        )
        return None
    except urllib.error.URLError as exc:
        logger.warning("Supabase %s: %s", path, exc.reason or exc)
        return None
    if not raw:
        return []
    return json.loads(raw.decode("utf-8"))


def fetch_session(base: str, token: str, class_code: str, session_date: str) -> dict[str, Any] | None:
    rows = _request(
        base,
        token,
        "class_sessions",
        query={
            "select": "id,class_code,session_date,started_at",
            "class_code": f"eq.{class_code}",
            "session_date": f"eq.{session_date}",
            "limit": "1",
        },
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def ensure_session(
    config: AppConfig,
    *,
    session_date: str | None = None,
) -> dict[str, Any] | None:
    base, token = _creds()
    if not base or not token:
        logger.warning("No se pudo abrir la sesión: faltan URL o clave de Supabase.")
        return None
    class_code = config.kiosk.web_class_code
    day = session_date or colombia_today()
    existing = fetch_session(base, token, class_code, day)
    if existing:
        return existing
    created = _request(
        base,
        token,
        "class_sessions",
        method="POST",
        body={
            "class_code": class_code,
            "session_date": day,
            "started_at": datetime.now(BOGOTA).isoformat(),
        },
        prefer="return=representation,resolution=ignore-duplicates",
    )
    if isinstance(created, list) and created:
        return created[0]
    if isinstance(created, dict) and created.get("id"):
        return created
    return fetch_session(base, token, class_code, day)


def record_pass(
    config: AppConfig,
    *,
    student_id: str,
    full_name: str,
    source: str = "kiosk",
    session_date: str | None = None,
) -> bool:
    if not student_id:
        return False
    session = ensure_session(config, session_date=session_date)
    if not session:
        return False
    base, token = _creds()
    result = _request(
        base,
        token,
        "attendance",
        method="POST",
        body={
            "class_code": session.get("class_code") or config.kiosk.web_class_code,
            "session_id": session["id"],
            "session_date": session.get("session_date") or colombia_today(),
            "student_id": student_id,
            "full_name": full_name,
            "source": source,
        },
        prefer="resolution=ignore-duplicates,return=minimal",
    )
    if result is None:
        return False
    logger.info("Asistencia registrada: %s (%s).", student_id, source)
    return True
