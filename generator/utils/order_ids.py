from sqlalchemy import text
from sqlalchemy.engine import Engine

from generator.utils.ids import next_id_start


def resolve_next_id_start(
    engine: Engine,
    table_name: str,
    id_column: str,
    prefix: str,
) -> int:
    query = text(f"SELECT {id_column} FROM {table_name}")
    with engine.connect() as connection:
        rows = connection.execute(query).fetchall()

    existing_ids = [row[0] for row in rows]
    return next_id_start(existing_ids, prefix)
