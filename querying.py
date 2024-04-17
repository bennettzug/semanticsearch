import psycopg2
from psycopg2 import sql
from courses_to_embeddings import generate_embedding


def get_most_similar_courses(
    conn, cur, query: str, school: str, n: int = 5
) -> list[tuple[any, ...]]:
    query_embedding = generate_embedding(query)
    embedding_table = f"{school.lower()}_embeddings"
    courses_table = f"{school.lower()}_courses"
    query = sql.SQL(
        """
        SELECT DISTINCT c.subject, c.number, c.name, c.description, c.credit_hours, 
       1 - (e.embedding <=> %s) AS cosine_similarity 
        FROM {et} e 
        JOIN {ct} c ON e.course_id = c.id 
        ORDER BY cosine_similarity DESC 
        LIMIT %s;
        """
    ).format(et=sql.Identifier(embedding_table), ct=sql.Identifier(courses_table))

    cur.execute(query, (query_embedding, n))
    results = cur.fetchall()
    new_results = []
    for row in results:
        list_row = list(row)
        hours = list_row[4]
        if "hours." in hours:
            list_row[4] = list_row[4].split("hours.")[0]
        new_results.append(tuple(list_row))

    return new_results


def main():
    conn = psycopg2.connect("dbname=vector_search user=postgres")
    cur = conn.cursor()

    query = input("Enter a query: ")
    results = get_most_similar_courses(conn, cur, query)
    print("Query:", query)
    print("Most similar courses:")
    for row in results:
        subject, number, name, description, credit_hours, cosine_similarity = row
        print(f"{subject} {number}: {name}")
        print(f"{description}")
        print(f"Credit Hours: {credit_hours}")
        print(f"Cosine Similarity: {cosine_similarity}")
        print("---")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
