import configparser
import psycopg2
import make_dbs


def main():
    config = configparser.ConfigParser()
    config.read("config.ini")

    try:
        conn = psycopg2.connect(
            dbname=config["database"]["dbname"],
            user=config["database"]["user"],
            password=config["database"]["password"],
            host=config["database"]["host"],
            port=config["database"]["port"],
        )
        cur = conn.cursor()

        input_schools = input(
            "Enter the schools you want to add separated by a space: "
        )
        schools = input_schools.split(" ")
        answer = input(
            f"This will delete if exists and rebuild databases for all of {schools} schools. Type 'I'm sure' to confirm.\n"
        )
        if answer != "I'm sure":
            print("Exiting...")
            return
        make_dbs.add_schools(conn, cur, schools)
        conn.commit()
        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)
        return


if __name__ == "__main__":
    main()
