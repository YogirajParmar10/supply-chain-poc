"""CLI for database schema migrations."""

from __future__ import annotations

import argparse

from generator.utils.db import get_engine
from generator.utils.migrations import (
    MIGRATIONS_DIR,
    baseline_migrations,
    migration_status,
    run_migrations,
)


def print_status() -> None:
    print(f"Migrations directory: {MIGRATIONS_DIR}")
    statuses = migration_status()
    if not statuses:
        print("No migration files found.")
        return

    for filename, status in statuses:
        print(f"  [{status}] {filename}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run database schema migrations.")
    parser.add_argument(
        "--status",
        action="store_true",
        help="List migrations and whether each has been applied.",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Mark all migrations as applied without executing SQL (for existing databases).",
    )
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.baseline:
        engine = get_engine()
        with engine.begin() as connection:
            marked = baseline_migrations(connection)
        print(f"Marked {marked} migration(s) as applied.")
        return

    applied = run_migrations()
    if not applied:
        print("No pending migrations.")
        return

    print(f"Applied {len(applied)} migration(s):")
    for filename in applied:
        print(f"  - {filename}")


if __name__ == "__main__":
    main()
