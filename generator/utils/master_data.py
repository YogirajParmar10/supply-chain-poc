import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Exact status values from schema/erp — excludes noisy bronze variants (DELIVERD, etc.).
PURCHASE_ORDER_RECEIPT_STATUSES: tuple[str, ...] = ("DELIVERED",)
SALES_ORDER_SHIPMENT_STATUSES: tuple[str, ...] = ("SHIPPED", "DELIVERED")


def load_materials(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("materials", con=engine)


def load_suppliers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("suppliers", con=engine)


def load_customers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("customers", con=engine)


def load_warehouses(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("warehouses", con=engine)


def load_delivered_purchase_orders(engine: Engine) -> pd.DataFrame:
    query = text(
        "SELECT * FROM purchase_orders WHERE status IN :statuses"
    ).bindparams(statuses=PURCHASE_ORDER_RECEIPT_STATUSES)
    return pd.read_sql(query, con=engine)


def load_shipped_sales_orders(engine: Engine) -> pd.DataFrame:
    query = text(
        "SELECT * FROM sales_orders WHERE status IN :statuses"
    ).bindparams(statuses=SALES_ORDER_SHIPMENT_STATUSES)
    return pd.read_sql(query, con=engine)
