from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from database import resolve_connection_kwargs

COURSE_COLUMNS = ("subject", "number", "name", "description", "credit_hours")
DATA_ROOT = Path("coursedata")


def make_courses_table(
    conn: Connection,
    cur: Cursor,
    school: str,
    csv_path: str | Path | None = None,
    *,
    drop_existing: bool = True,
) -> int:
    """Create or replace a school's course catalog entries in the shared table."""

    school_key = school.upper()
    target_csv = Path(csv_path) if csv_path else _default_csv_for_school(school)
    if not target_csv.exists():
        raise FileNotFoundError(
            f"Could not locate course CSV for {school_key}: {target_csv}"
        )

    _ensure_courses_table(cur)

    if drop_existing:
        cur.execute("DELETE FROM courses WHERE school = %s", (school_key,))

    rows = list(_iter_course_rows(target_csv))
    if not rows:
        return 0

    insert_statement = """
        INSERT INTO courses (school, subject, number, name, description, credit_hours)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

    for row in rows:
        cur.execute(insert_statement, (school_key, *row))

    return len(rows)


def _iter_course_rows(csv_path: Path) -> Iterable[tuple[str, str, str, str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for raw in reader:
            if not raw:
                continue
            normalized = {
                key.strip().lower(): (value or "").strip() for key, value in raw.items()
            }
            subject = normalized.get("subject")
            number = normalized.get("number")
            name = normalized.get("name")
            description = normalized.get("description")
            credit_hours = _resolve_credit_value(normalized)

            if not all([subject, number, name]):
                continue

            yield (subject, number, name, description or "", credit_hours or "")


def _default_csv_for_school(school: str) -> Path:
    school_key = school.lower()
    return DATA_ROOT / school_key / f"{school.upper()}_courses.csv"


def _ensure_courses_table(cur: Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id SERIAL PRIMARY KEY,
            school TEXT NOT NULL,
            subject TEXT NOT NULL,
            number TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            credit_hours TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_school ON courses (school)")


def _resolve_credit_value(columns: dict[str, str]) -> str:
    candidates = (
        "credit hours",
        "credit_hours",
        "credits",
        "credit",
        "hours",
    )
    for key in candidates:
        if key in columns and columns[key]:
            return columns[key]

    for key, value in columns.items():
        if "credit" in key and "hour" in key and value:
            return value

    return ""


def _connection_kwargs(database_url: str | None) -> dict[str, str]:
    if database_url:
        return {"dsn": database_url}
    return resolve_connection_kwargs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or refresh a school's course table entries."
    )
    parser.add_argument(
        "--school", required=True, help="Short code for the school (e.g. ASU, UIUC)."
    )
    parser.add_argument(
        "--csv-path",
        help="Override path to the source CSV. Defaults to coursedata/<school>/<SCHOOL>_courses.csv.",
    )
    parser.add_argument(
        "--database-url",
        help="Optional PostgreSQL DSN to override config/env discovery.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Retain existing rows before inserting.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt (use in automation).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.yes:
        confirmation = input(
            f"This will replace the {args.school.upper()} course catalog. Type 'I'm sure' to continue: "
        )
        if confirmation.strip() != "I'm sure":
            print("Aborting without changes.")
            return

    kwargs = _connection_kwargs(args.database_url)
    conn = psycopg2.connect(**kwargs)
    cur = conn.cursor()

    try:
        inserted = make_courses_table(
            conn,
            cur,
            args.school,
            csv_path=args.csv_path,
            drop_existing=not args.keep_existing,
        )
        conn.commit()
        print(f"Loaded {inserted} courses for {args.school.upper()} into PostgreSQL.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
