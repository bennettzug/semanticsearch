from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Mapping

import psycopg2
from flask import Flask, Response, current_app, g, jsonify, request, send_from_directory
from psycopg2 import errors
from psycopg2.extensions import cursor as PsycopgCursor
from psycopg2.pool import SimpleConnectionPool
from werkzeug.middleware.proxy_fix import ProxyFix

from database import resolve_connection_kwargs
from querying import get_most_similar_courses


def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__, static_folder="client/dist", static_url_path="")

    # Honour reverse proxies such as load balancers (needed for production deployments).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # type: ignore[arg-type]

    _initialise_connection_pool(app)
    _register_routes(app)

    return app


def _register_routes(app: Flask) -> None:
    @app.route("/")
    def index() -> tuple[str, int] | str:
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/healthz", methods=["GET"])
    def healthcheck() -> Response:
        return jsonify({"status": "ok"})

    @app.route("/search", methods=["GET", "POST"])
    def search() -> Response:
        payload: Mapping[str, object]
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
        else:
            payload = request.args

        query = str(payload.get("query") or "").strip()
        school = str(payload.get("school") or "").strip().upper()
        raw_limit = payload.get("limit") or request.args.get("limit", type=int)

        if not query:
            return jsonify({"error": "'query' is required."}), 400

        try:
            limit = int(raw_limit) if raw_limit is not None else 10
        except (TypeError, ValueError):
            return jsonify({"error": "'limit' must be an integer."}), 400

        limit = max(1, min(limit, 50))

        resolved_school = None if school in {"", "ALL", "*"} else school

        try:
            with _get_db_cursor() as cursor:
                results = get_most_similar_courses(
                    cursor, query=query, school=resolved_school, limit=limit
                )
        except errors.UndefinedTable:
            current_app.logger.exception(
                "Database tables missing during search request"
            )
            return (
                jsonify(
                    {
                        "error": "Course data not initialised. Run the data loading scripts (make_dbs.py) and retry.",
                    }
                ),
                503,
            )
        except psycopg2.Error as exc:
            current_app.logger.exception(
                "Unexpected database error during search request"
            )
            error_payload = {"error": "Search failed due to a database error."}
            if exc.pgerror:
                error_payload["detail"] = exc.pgerror.strip()
            return jsonify(error_payload), 500
        except Exception:
            current_app.logger.exception("Unhandled error during search request")
            return jsonify({"error": "Search failed due to an unexpected error."}), 500

        return jsonify({"results": results})


def _initialise_connection_pool(app: Flask) -> None:
    minconn = int(os.getenv("DATABASE_MIN_CONNECTIONS", "1"))
    maxconn = int(os.getenv("DATABASE_MAX_CONNECTIONS", "5"))
    if maxconn < minconn:
        raise ValueError(
            "DATABASE_MAX_CONNECTIONS must be greater than or equal to DATABASE_MIN_CONNECTIONS"
        )

    connection_kwargs = resolve_connection_kwargs()

    app.config["DB_POOL"] = SimpleConnectionPool(
        minconn=minconn, maxconn=maxconn, **connection_kwargs
    )

    @app.teardown_appcontext
    def _close_db_connection(_: Exception | None) -> None:
        connection = g.pop("db_conn", None)
        if not connection:
            return

        # Always rollback to leave the connection in a clean state for the pool.
        connection.rollback()
        pool: SimpleConnectionPool = current_app.config["DB_POOL"]
        pool.putconn(connection)


def _get_db_connection():
    if "db_conn" not in g:
        pool: SimpleConnectionPool = current_app.config["DB_POOL"]
        g.db_conn = pool.getconn()
    return g.db_conn


@contextmanager
def _get_db_cursor() -> Iterator[PsycopgCursor]:
    connection = _get_db_connection()
    cursor = connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
