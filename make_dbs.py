from __future__ import annotations

import argparse
from typing import Iterable, Sequence

import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from courses_to_embeddings import make_embeddings_table
from create_courses_table import make_courses_table
from database import resolve_connection_kwargs


def add_schools(
    conn: Connection,
    cur: Cursor,
    schools: Iterable[str],
    *,
    drop_courses: bool = True,
    drop_embeddings: bool = True,
    embedding_limit: int | None = None,
) -> tuple[int, int]:
    total_courses = 0
    total_embeddings = 0

    for school in schools:
        school_display = school.upper()
        print(f"Preparing data for {school_display}…")

        inserted_courses = make_courses_table(
            conn,
            cur,
            school,
            drop_existing=drop_courses,
        )
        conn.commit()
        total_courses += inserted_courses
        print(f"  - Loaded {inserted_courses} course rows")

        generated = make_embeddings_table(
            conn,
            cur,
            school,
            drop_existing=drop_embeddings,
            limit=embedding_limit,
        )
        conn.commit()
        total_embeddings += generated
        print(f"  - Generated {generated} embeddings")

    return total_courses, total_embeddings


def _connection_kwargs(database_url: str | None) -> dict[str, str]:
    if database_url:
        return {"dsn": database_url}
    return resolve_connection_kwargs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap course tables and embeddings for one or more schools."
    )
    parser.add_argument(
        "schools",
        nargs="+",
        help="One or more school short codes (e.g. ASU UIUC UNC).",
    )
    parser.add_argument(
        "--database-url",
        help="Optional PostgreSQL DSN to override config/env discovery.",
    )
    parser.add_argument(
        "--keep-courses",
        action="store_true",
        help="Do not delete existing course rows for the school before loading.",
    )
    parser.add_argument(
        "--keep-embeddings",
        action="store_true",
        help="Do not delete existing embeddings for the school before loading.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Generate embeddings for only the first N courses (useful for smoke tests).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt (use in automation).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    schools: Sequence[str] = [
        school.strip() for school in args.schools if school.strip()
    ]
    if not schools:
        raise ValueError("At least one school code must be provided.")

    if not args.yes:
        confirmation = input(
            "This will rebuild course and embedding tables for "
            f"{', '.join(code.upper() for code in schools)}. Type 'I'm sure' to continue: "
        )
        if confirmation.strip() != "I'm sure":
            print("Aborting without changes.")
            return

    kwargs = _connection_kwargs(args.database_url)
    conn = psycopg2.connect(**kwargs)
    cur = conn.cursor()

    try:
        course_count, embedding_count = add_schools(
            conn,
            cur,
            schools,
            drop_courses=not args.keep_courses,
            drop_embeddings=not args.keep_embeddings,
            embedding_limit=args.limit,
        )
        print(
            "Finished bootstrapping data: "
            f"{course_count} courses, {embedding_count} embeddings for {len(schools)} school(s)."
        )
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
