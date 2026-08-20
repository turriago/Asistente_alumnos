"""Aplica supabase/schema.sql usando DATABASE_URL del .env. No imprime secretos."""

from __future__ import annotations

import os

import psycopg

from attendance_system.config import PROJECT_ROOT
from attendance_system.supabase_sync import load_env_file


def main() -> None:
    load_env_file()
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("Falta DATABASE_URL en .env")
    sql = (PROJECT_ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(url) as conn:
        conn.execute(sql)
        conn.commit()
        tables = conn.execute(
            "select tablename from pg_tables where schemaname='public' order by 1"
        ).fetchall()
        buckets = conn.execute(
            "select id, public from storage.buckets where id='student-media'"
        ).fetchall()
    print("tablas:", ", ".join(row[0] for row in tables))
    print("bucket:", buckets)


if __name__ == "__main__":
    main()
