import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass


_load_env()


def get_database_url() -> str:
    required_vars = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    if all(os.getenv(var) for var in required_vars):
        host = os.environ["DB_HOST"]
        port = os.getenv("DB_PORT", "5432")
        name = os.environ["DB_NAME"]
        user = os.environ["DB_USER"]
        password = os.environ["DB_PASSWORD"]
        return (
            f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{name}"
        )

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    raise ValueError(
        "Database credentials not configured. Set DATABASE_URL or: "
        + ", ".join(required_vars)
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_database_url())
