import pandas as pd
from sqlalchemy.engine import Engine

from generator.wms.warehouses import dedupe_bronze_orders

# Exact status values from schema/erp — excludes noisy bronze variants (DELIVERD, etc.).
PURCHASE_ORDER_RECEIPT_STATUSES: frozenset[str] = frozenset({"DELIVERED"})
SALES_ORDER_SHIPMENT_STATUSES: frozenset[str] = frozenset({"SHIPPED", "DELIVERED"})


def load_materials(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("materials", con=engine)


def load_suppliers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("suppliers", con=engine)


def load_customers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("customers", con=engine)


def load_warehouses(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("warehouses", con=engine)


def load_purchase_orders(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("purchase_orders", con=engine)


def load_sales_orders(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("sales_orders", con=engine)


def load_inventory_transactions(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("inventory_transactions", con=engine)


def load_goods_receipt_reference_ids(engine: Engine) -> set[str]:
    inventory_transactions = load_inventory_transactions(engine)
    if inventory_transactions.empty:
        return set()

    goods_receipts = inventory_transactions[
        inventory_transactions["transaction_type"] == "GOODS_RECEIPT"
    ]
    if goods_receipts.empty:
        return set()

    return set(goods_receipts["reference_id"].dropna().astype(str))


def load_clean_delivered_purchase_orders(engine: Engine) -> pd.DataFrame:
    purchase_orders = load_purchase_orders(engine)
    purchase_orders = dedupe_bronze_orders(purchase_orders, "purchase_order_id")
    return purchase_orders[
        purchase_orders["status"].isin(PURCHASE_ORDER_RECEIPT_STATUSES)
    ].reset_index(drop=True)


def load_clean_shipped_sales_orders(engine: Engine) -> pd.DataFrame:
    sales_orders = load_sales_orders(engine)
    sales_orders = dedupe_bronze_orders(sales_orders, "sales_order_id")
    return sales_orders[
        sales_orders["status"].isin(SALES_ORDER_SHIPMENT_STATUSES)
    ].reset_index(drop=True)
