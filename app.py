from flask import Flask, request, jsonify, render_template
import psycopg2
import configparser
from querying import get_most_similar_courses

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.json.get("query")
        selected_school = request.json.get("school")
    elif request.method == "GET":
        query = request.args.get("query")
        selected_school = request.args.get("school")
    else:
        return "Method Not Allowed", 405

    if not query or not selected_school:
        return "Query or school parameter is missing", 400

    config = configparser.ConfigParser()
    config.read("config.ini")

    
    conn = psycopg2.connect(
            dbname=config['database']['dbname'],
            user=config['database']['user'],
            password=config['database']['password'],
            host=config['database']['host'],
            port=config['database']['port']
        )
    cur = conn.cursor()
 

    search_results = get_most_similar_courses(conn, cur, query, selected_school, n=10)
    return jsonify(search_results)


if __name__ == "__main__":
    app.run(port=8000)
