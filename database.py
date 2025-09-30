from __future__ import annotations

import configparser
import os
from typing import Dict


def resolve_connection_kwargs(config_path: str = "config.ini") -> Dict[str, str]:
    """Resolve PostgreSQL connection parameters from env vars or config file."""

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}

    parser = configparser.ConfigParser()
    if parser.read(config_path) and "database" in parser:
        section = parser["database"]
        required_keys = {"dbname", "user", "password", "host", "port"}
        missing_keys = required_keys - set(section)
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise KeyError(f"Missing database configuration values: {missing}")

        return {key: section[key] for key in required_keys}

    raise RuntimeError(
        "Database configuration not found. Set DATABASE_URL or provide config.ini with credentials."
    )
