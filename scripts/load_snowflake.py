"""
Load master, WMS, and MES data from PostgreSQL into Snowflake.

Reads the tables mapped to Snowflake (master data + warehouse/inventory
data, plus production data replicated here for local joins against
inventory) and loads them into FLEXIPACK.PUBLIC, replacing each table's
contents on every run.

The generator produces a deterministic dataset (fixed seed), so a full
replace per table is simpler and safer here than an incremental upsert --
there is no risk of losing history, since there is no independent history
being tracked on the Snowflake side.

Required .env additions:
    SF_ACCOUNT=mzzcfjf-xk89203
    SF_USER=<snowflake username>
    SF_PASSWORD=<snowflake password>
    SF_WAREHOUSE=COMPUTE_WH
    SF_DATABASE=FLEXIPACK
    SF_SCHEMA=PUBLIC

Usage:
    python -m scripts.load_snowflake
"""

import os
import sys

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from sqlalchemy import text

from generator.utils.db import get_engine

# (postgres table, snowflake table, columns to select from postgres)
LOADS = [
    ("plants", "PLANTS", "*"),
    ("warehouses", "WAREHOUSES", "*"),
    (
        "production_orders",
        "PRODUCTION_ORDERS",
        "production_order_id, plant_id, material_id, planned_quantity, "
        "actual_quantity, start_date, end_date, status",
    ),
    (
        "production_output",
        "PRODUCTION_OUTPUT",
        "production_output_id, production_order_id, input_material_id, "
        "input_quantity, output_material_id, output_quantity",
    ),
]

REQUIRED_ENV_VARS = ("SF_ACCOUNT", "SF_USER", "SF_PASSWORD", "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA")


def get_connection() -> snowflake.connector.SnowflakeConnection:
    if not all(os.getenv(var) for var in REQUIRED_ENV_VARS):
        sys.exit(f"Set {', '.join(REQUIRED_ENV_VARS)} in .env")

    return snowflake.connector.connect(
        account=os.environ["SF_ACCOUNT"],
        user=os.environ["SF_USER"],
        password=os.environ["SF_PASSWORD"],
        warehouse=os.environ["SF_WAREHOUSE"],
        database=os.environ["SF_DATABASE"],
        schema=os.environ["SF_SCHEMA"],
    )


def load_table(conn, pg_table: str, sf_table: str, columns: str) -> None:
    with get_engine().connect() as pg_conn:
        df = pd.read_sql(text(f"SELECT {columns} FROM {pg_table}"), pg_conn)

    # The tables already in Snowflake use lowercase quoted column names
    # (created by the CSV upload wizard). Keep that convention so the
    # replaced table's columns match what earlier SQL queries expect.
    df.columns = [c.lower() for c in df.columns]

    _, _, rows, _ = write_pandas(
        conn,
        df,
        sf_table,
        auto_create_table=True,
        overwrite=True,
        quote_identifiers=True,
        use_logical_type=True,
    )
    print(f"{sf_table}: replaced with {rows} rows")


def main() -> None:
    conn = get_connection()
    try:
        for pg_table, sf_table, columns in LOADS:
            load_table(conn, pg_table, sf_table, columns)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
