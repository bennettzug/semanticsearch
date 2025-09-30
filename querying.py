from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import cursor

from courses_to_embeddings import generate_embedding

CourseResult = Dict[str, Any]


def get_most_similar_courses(
    cur: cursor,
    *,
    query: str,
    school: Optional[str] = None,
    limit: int = 5,
) -> List[CourseResult]:
    """Return the most similar courses for a free-text query."""

    query_embedding = generate_embedding(query)
    school_filter = sql.SQL("WHERE c.school = %s") if school else sql.SQL("")

    statement = sql.SQL(
        """
        SELECT
            c.school,
            c.subject,
            c.number,
            c.name,
            c.description,
            c.credit_hours,
            1 - (ce.embedding <=> %s) AS cosine_similarity
        FROM course_embeddings AS ce
        JOIN courses AS c ON ce.course_id = c.id
        {school_filter}
        ORDER BY cosine_similarity DESC
        LIMIT %s
        """
    ).format(school_filter=school_filter)

    params: tuple[Any, ...]
    if school:
        params = (query_embedding, school.upper(), limit)
    else:
        params = (query_embedding, limit)

    cur.execute(statement, params)
    rows = cur.fetchall()

    return [_map_row_to_result(row) for row in rows]


def _map_row_to_result(row: Iterable[Any]) -> CourseResult:
    school, subject, number, name, description, credit_hours, similarity = row
    return {
        "school": school,
        "subject": subject,
        "number": number,
        "name": name,
        "description": description,
        "creditHours": _normalise_credit_hours(credit_hours),
        "similarity": _normalise_similarity(similarity),
    }


def _normalise_credit_hours(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    if "hour" in text:
        text = text.replace("hours.", "").replace("hour.", "").strip()

    return text


def _normalise_similarity(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    conn = psycopg2.connect("dbname=vector_search user=postgres")
    cur = conn.cursor()

    query = input("Enter a query: ")
    school = input("Enter a school code (blank for all): ") or None
    results = get_most_similar_courses(cur, query=query, school=school)
    print("Query:", query)
    print("Most similar courses:")
    for result in results:
        print(
            f"{result['school']} | {result['subject']} {result['number']}: {result['name']}"
        )
        print(result["description"])
        print(f"Credit Hours: {result['creditHours']}")
        print(f"Cosine Similarity: {result['similarity']}")
        print("---")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
