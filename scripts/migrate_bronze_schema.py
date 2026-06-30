"""Apply bronze-layer schema migration for transactional tables."""

from pathlib import Path

from sqlalchemy import text

from generator.utils.db import get_engine


def main() -> None:
    sql_path = Path(__file__).resolve().parents[1] / "schema" / "migrate_bronze_transactional.sql"
    migration_sql = sql_path.read_text()

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(migration_sql))

    print("Bronze schema migration applied successfully.")
    print(f"  - source: {sql_path}")


if __name__ == "__main__":
    main()
