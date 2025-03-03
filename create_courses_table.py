import csv

import psycopg2
from psycopg2 import sql


def make_courses_table(conn, cur, school):
    courses_table = f"{school.lower()}_courses"
    # cur.execute(f"""
    #     DROP TABLE IF EXISTS {school}_courses
    #     """)
    cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(courses_table)))

    cur.execute(
        sql.SQL("""
        CREATE TABLE IF NOT EXISTS {} (
            id SERIAL PRIMARY KEY,
            subject TEXT NOT NULL,
            number TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            credit_hours TEXT NOT NULL
        )
    """).format(sql.Identifier(courses_table))
    )

    with open(f"coursedata/{school.lower()}/{school}_courses.csv", "r") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row

        for row in reader:
            subject, number, name, description, credit_hours = row
            cur.execute(
                sql.SQL(
                    "INSERT INTO {} (subject, number, name, description, credit_hours) VALUES (%s, %s, %s, %s, %s)"
                ).format(sql.Identifier(courses_table)),
                (subject, number, name, description, credit_hours),
            )


def main():
    # Connect to the PostgreSQL database
    conn = psycopg2.connect("dbname=vector_search user=postgres")
    cur = conn.cursor()
    print("This drops the existing courses table and creates a new one.")
    answer = input("Are you sure you want to create the courses table? Type 'I'm sure' to continue: ")
    if answer != "I'm sure":
        print("Exiting...")
        return
    # Create the courses table
    make_courses_table(conn, cur, "ASU")


if __name__ == "__main__":
    main()
