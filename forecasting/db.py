"""Database helpers for the forecasting package."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from generator.utils.db import get_engine

SQL_DIR = Path(__file__).resolve().parent / "sql"


def get_forecast_engine() -> Engine:
    """Reuse the project DATABASE_URL / .env connection."""
    return get_engine()


def run_sql_file(engine: Engine, path: Path) -> None:
    sql = path.read_text()
    with engine.begin() as conn:
        conn.execute(text(sql))


def apply_forecast_sql(engine: Engine | None = None) -> list[str]:
    """Apply forecasting/*.sql files in sorted order."""
    engine = engine or get_forecast_engine()
    applied: list[str] = []
    for path in sorted(SQL_DIR.glob("*.sql")):
        run_sql_file(engine, path)
        applied.append(path.name)
    return applied


def qualified(schema: str, table: str) -> str:
    return f"{schema}.{table}"
