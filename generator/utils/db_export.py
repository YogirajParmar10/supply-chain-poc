import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

TABLE_PRIMARY_KEYS: dict[str, str] = {
    "materials": "material_id",
    "suppliers": "supplier_id",
    "customers": "customer_id",
    "plants": "plant_id",
    "warehouses": "warehouse_id",
}

# Transactional bronze tables append raw rows (duplicates allowed).
BRONZE_APPEND_TABLES: frozenset[str] = frozenset({
    "purchase_orders",
    "sales_orders",
    "inventory_transactions",
})


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
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_cols,
        )
        conn.execute(stmt)

    return upsert


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

    table_exists = inspect(engine).has_table(table_name)
    primary_key = conflict_column or TABLE_PRIMARY_KEYS.get(table_name)

    if table_name in BRONZE_APPEND_TABLES:
        method = None
    elif not table_exists:
        method = None
    else:
        method = _upsert_method([primary_key]) if primary_key else None

    df.to_sql(
        table_name,
        con=engine,
        if_exists="append",
        index=False,
        method=method,
    )

    if not table_exists and primary_key and table_name not in BRONZE_APPEND_TABLES:
        _ensure_primary_key(engine, table_name, primary_key)

    return len(df)


def read_table(table_name: str, engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table(table_name, con=engine)
