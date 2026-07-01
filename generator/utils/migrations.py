"""Database schema migration utilities."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from generator.utils.db import get_engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_migrations_applied = False


def list_migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def migration_version(path: Path) -> str:
    return path.stem


def ensure_migrations_table(connection) -> None:
    connection.execute(text(SCHEMA_MIGRATIONS_DDL))


def get_applied_versions(connection) -> set[str]:
    rows = connection.execute(text("SELECT version FROM schema_migrations")).fetchall()
    return {row[0] for row in rows}


def apply_migration(connection, migration_path: Path) -> None:
    connection.execute(text(migration_path.read_text()))
    connection.execute(
        text(
            """
            INSERT INTO schema_migrations (version, filename)
            VALUES (:version, :filename)
            """
        ),
        {
            "version": migration_version(migration_path),
            "filename": migration_path.name,
        },
    )


def run_migrations() -> list[str]:
    migration_files = list_migration_files()
    if not migration_files:
        return []

    engine = get_engine()
    applied: list[str] = []

    with engine.begin() as connection:
        ensure_migrations_table(connection)
        applied_versions = get_applied_versions(connection)

        for migration_path in migration_files:
            version = migration_version(migration_path)
            if version in applied_versions:
                continue

            apply_migration(connection, migration_path)
            applied.append(migration_path.name)

    return applied


def baseline_migrations(connection) -> int:
    ensure_migrations_table(connection)
    applied_versions = get_applied_versions(connection)
    marked = 0

    for migration_path in list_migration_files():
        version = migration_version(migration_path)
        if version in applied_versions:
            continue

        connection.execute(
            text(
                """
                INSERT INTO schema_migrations (version, filename)
                VALUES (:version, :filename)
                """
            ),
            {"version": version, "filename": migration_path.name},
        )
        marked += 1

    return marked


def ensure_migrations_applied() -> list[str]:
    """Apply pending migrations once per process before database writes."""
    global _migrations_applied
    if _migrations_applied:
        return []

    applied = run_migrations()
    _migrations_applied = True
    return applied


def migration_status() -> list[tuple[str, str]]:
    migration_files = list_migration_files()
    engine = get_engine()

    with engine.connect() as connection:
        ensure_migrations_table(connection)
        applied_versions = get_applied_versions(connection)

    return [
        (
            migration_path.name,
            "applied" if migration_version(migration_path) in applied_versions else "pending",
        )
        for migration_path in migration_files
    ]
