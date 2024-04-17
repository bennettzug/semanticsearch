import psycopg2
from embeddings_gen import generate_embedding
from psycopg2 import sql


def make_embeddings_table(conn, cur, school):
    embedding_table = f"{school.lower()}_embeddings"
    courses_table = f"{school.lower()}_courses"
    # cur.execute(f"""
    #     DROP TABLE IF EXISTS {school}_embeddings
    #     """)
    cur.execute(
        sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(embedding_table))
    )

    # cur.execute(f"""
    #     CREATE TABLE IF NOT EXISTS {school}_embeddings (
    #         id SERIAL PRIMARY KEY,
    #         description TEXT NOT NULL,
    #         embedding VECTOR(768) NOT NULL,
    #         course_id INTEGER REFERENCES {school}_courses(id)
    #     )
    # """)
    cur.execute(
        sql.SQL("""
        CREATE TABLE IF NOT EXISTS {et} (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            embedding VECTOR(768) NOT NULL,
            course_id INTEGER REFERENCES {ct}(id)
        )
    """).format(et=sql.Identifier(embedding_table), ct=sql.Identifier(courses_table))
    )

    # cur.execute(f"SELECT id, subject, number, name, description FROM {school}_courses")
    cur.execute(
        sql.SQL("SELECT id, subject, number, name, description FROM {}").format(
            sql.Identifier(courses_table)
        )
    )

    course_data = cur.fetchall()
    i = 0
    for course_id, subject, number, name, description in course_data:
        embedding_str = generate_embedding(
            subject + " " + number + " " + name + " " + description
        )

        # cur.execute(
        #     f"INSERT INTO {school}_embeddings (description, embedding, course_id) VALUES (%s, %s, %s)",
        #     (description, embedding_str, course_id),
        # )
        cur.execute(
            sql.SQL(
                "INSERT INTO {} (description, embedding, course_id) VALUES (%s, %s, %s)"
            ).format(sql.Identifier(embedding_table)),
            (description, embedding_str, course_id),
        )
        print(f"Inserted embedding for course {name} ({i + 1}/{len(course_data)})")
        i += 1


def main():
    # Connect to the PostgreSQL database
    conn = psycopg2.connect("dbname=vector_search user=postgres")
    cur = conn.cursor()
    print("This drops the existing embeddings table and creates a new one.")
    answer = input(
        "Are you sure you want to create the embeddings table? Type 'I'm sure' to continue: "
    )
    if answer != "I'm sure":
        print("Exiting...")
        return
    # Create the embeddings table
    make_embeddings_table(conn, cur, "ASU")
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
