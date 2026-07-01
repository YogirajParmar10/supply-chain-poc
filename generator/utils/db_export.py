import pandas as pd
from sqlalchemy import func, inspect, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from generator.utils.migrations import ensure_migrations_applied

TABLE_PRIMARY_KEYS: dict[str, str] = {
    "materials": "material_id",
    "suppliers": "supplier_id",
    "customers": "customer_id",
    "plants": "plant_id",
    "warehouses": "warehouse_id",
}

TIMESTAMP_COLUMNS: tuple[str, ...] = ("created_at", "updated_at")

# Transactional bronze tables append raw rows (duplicates allowed).
BRONZE_APPEND_TABLES: frozenset[str] = frozenset({
    "purchase_orders",
    "sales_orders",
    "inventory_transactions",
})

# Snapshot tables are fully replaced on each generation run.
SNAPSHOT_TABLES: frozenset[str] = frozenset({"inventory"})


def _upsert_method(conflict_columns: list[str]):
    def upsert(table, conn, keys, data_iter):
        rows = [dict(zip(keys, row)) for row in data_iter]
        if not rows:
            return

        stmt = insert(table.table).values(rows)
        update_cols = {
            column.name: stmt.excluded[column.name]
            for column in table.table.columns
            if column.name not in conflict_columns
            and column.name not in TIMESTAMP_COLUMNS
        }
        if "updated_at" in table.table.c:
            update_cols["updated_at"] = func.now()

        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_cols,
        )
        conn.execute(stmt)

    return upsert


def _truncate_table(engine: Engine, table_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f'TRUNCATE TABLE "{table_name}"'))


def _ensure_timestamp_columns(engine: Engine, table_name: str) -> None:
    with engine.begin() as conn:
        for column_name in TIMESTAMP_COLUMNS:
            conn.execute(
                text(
                    f'ALTER TABLE "{table_name}" '
                    f"ADD COLUMN IF NOT EXISTS {column_name} "
                    f"TIMESTAMPTZ NOT NULL DEFAULT NOW()"
                )
            )


def _ensure_primary_key(engine: Engine, table_name: str, primary_key: str) -> None:
    inspector = inspect(engine)
    pk_constraint = inspector.get_pk_constraint(table_name)
    if pk_constraint.get("constrained_columns"):
        return

    with engine.begin() as conn:
        conn.execute(
            text(f'ALTER TABLE "{table_name}" ADD PRIMARY KEY ("{primary_key}")')
        )


def write_dataframe(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    *,
    conflict_column: str | None = None,
) -> int:
    if df.empty:
        return 0

    ensure_migrations_applied()

    table_exists = inspect(engine).has_table(table_name)
    primary_key = conflict_column or TABLE_PRIMARY_KEYS.get(table_name)

    if table_name in SNAPSHOT_TABLES:
        if table_exists:
            _truncate_table(engine, table_name)
        if_exists = "append"
        method = None
    elif table_name in BRONZE_APPEND_TABLES:
        if_exists = "append"
        method = None
    elif not table_exists:
        if_exists = "append"
        method = None
    else:
        if_exists = "append"
        method = _upsert_method([primary_key]) if primary_key else None

    df.to_sql(
        table_name,
        con=engine,
        if_exists=if_exists,
        index=False,
        method=method,
    )

    if not table_exists and primary_key and table_name not in BRONZE_APPEND_TABLES:
        _ensure_primary_key(engine, table_name, primary_key)

    _ensure_timestamp_columns(engine, table_name)

    return len(df)


def read_table(table_name: str, engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table(table_name, con=engine)
