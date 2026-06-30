import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

TABLE_PRIMARY_KEYS: dict[str, str] = {
    "materials": "material_id",
    "suppliers": "supplier_id",
    "customers": "customer_id",
    "plants": "plant_id",
    "warehouses": "warehouse_id",
    "purchase_orders": "purchase_order_id",
    "sales_orders": "sales_order_id",
}


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


def write_dataframe(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    *,
    conflict_column: str | None = None,
) -> int:
    if df.empty:
        return 0

    primary_key = conflict_column or TABLE_PRIMARY_KEYS.get(table_name)
    method = _upsert_method([primary_key]) if primary_key else None

    df.to_sql(
        table_name,
        con=engine,
        if_exists="append",
        index=False,
        method=method,
    )
    return len(df)


def read_table(table_name: str, engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table(table_name, con=engine)
