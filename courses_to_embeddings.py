from __future__ import annotations

import argparse

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor
from tqdm import tqdm

from database import resolve_connection_kwargs
from embeddings_gen import generate_embedding


def make_embeddings_table(
    conn: Connection,
    cur: Cursor,
    school: str,
    *,
    drop_existing: bool = True,
    limit: int | None = None,
) -> int:
    """Generate embeddings for a school's catalog and persist them in pgvector."""

    school_key = school.upper()
    _ensure_embeddings_table(cur)

    course_ids = _select_course_rows(cur, school_key, limit=limit)
    if not course_ids:
        return 0

    if drop_existing:
        cur.execute(
            "DELETE FROM course_embeddings WHERE course_id = ANY(%s)",
            ([course_id for course_id, *_ in course_ids],),
        )

    insert_statement = sql.SQL(
        """
        INSERT INTO course_embeddings (description, embedding, course_id)
        VALUES (%s, %s, %s)
        """
    )

    progress = tqdm(
        course_ids, desc=f"Embedding {school_key} courses", unit="course", disable=False
    )
    for course_id, subject, number, name, description in progress:
        parts = [
            subject,
            str(number) if number is not None else "",
            name,
            description,
        ]
        prompt = " ".join(part for part in parts if part)
        embedding_str = generate_embedding(prompt)
        cur.execute(insert_statement, (description, embedding_str, course_id))

    return len(course_ids)


def _ensure_embeddings_table(cur: Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS course_embeddings (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            embedding VECTOR(768) NOT NULL,
            course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_course_embeddings_course_id ON course_embeddings (course_id)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_course_embeddings_course_id ON course_embeddings (course_id)"
    )


def _select_course_rows(
    cur: Cursor, school: str, *, limit: int | None = None
) -> list[tuple[int, str, str, str, str]]:
    statement = sql.SQL(
        "SELECT id, subject, number, name, description FROM courses WHERE school = %s ORDER BY id"
    )
    params: tuple = (school,)
    if limit is not None and limit > 0:
        statement += sql.SQL(" LIMIT %s")
        params += (limit,)

    cur.execute(statement, params)
    return cur.fetchall()


def _connection_kwargs(database_url: str | None) -> dict[str, str]:
    if database_url:
        return {"dsn": database_url}
    return resolve_connection_kwargs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or refresh the pgvector embeddings table for a school."
    )
    parser.add_argument(
        "--school", required=True, help="Short code for the school (e.g. ASU, UIUC)."
    )
    parser.add_argument(
        "--database-url",
        help="Optional PostgreSQL DSN to override config/env discovery.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not delete existing embeddings first.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process only the first N courses (useful for smoke tests).",
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
        message = f"This will regenerate embeddings for {args.school.upper()} courses. Type 'I'm sure' to continue: "
        confirmation = input(message)
        if confirmation.strip() != "I'm sure":
            print("Aborting without changes.")
            return

    kwargs = _connection_kwargs(args.database_url)
    conn = psycopg2.connect(**kwargs)
    cur = conn.cursor()

    try:
        processed = make_embeddings_table(
            conn,
            cur,
            args.school,
            drop_existing=not args.keep_existing,
            limit=args.limit,
        )
        conn.commit()
        print(f"Generated embeddings for {processed} courses at {args.school.upper()}.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
