import configparser
import psycopg2
import create_courses_table
import courses_to_embeddings


def main():
    config = configparser.ConfigParser()
    config.read("config.ini")

    try:
        conn = psycopg2.connect(
            dbname=config['database']['dbname'],
            user=config['database']['user'],
            password=config['database']['password'],
            host=config['database']['host'],
            port=config['database']['port']
        )
        cur = conn.cursor()
        schools = ["ASU", "UIUC"]
        answer = input(f"this will delete and rebuild databases for all of {schools}. Type 'I'm sure' to confirm.\n")
        if answer != "I'm sure":
            print("exiting...")
            return
        for school in schools:
            create_courses_table.make_courses_table(conn,cur,school)
            courses_to_embeddings.make_embeddings_table(conn,cur,school)

        conn.commit()
        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)

    


if __name__ == "__main__":
    main()
