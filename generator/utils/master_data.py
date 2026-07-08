import pandas as pd
from sqlalchemy.engine import Engine

from generator.wms.warehouses import dedupe_bronze_orders

# Exact status values from schema/erp — excludes noisy bronze variants (DELIVERD, etc.).
PURCHASE_ORDER_RECEIPT_STATUSES: frozenset[str] = frozenset({"DELIVERED"})
SALES_ORDER_SHIPMENT_STATUSES: frozenset[str] = frozenset({"SHIPPED", "DELIVERED"})
PRODUCTION_ORDER_OUTPUT_STATUSES: frozenset[str] = frozenset({"COMPLETED"})


def load_materials(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("materials", con=engine)


def load_suppliers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("suppliers", con=engine)


def load_active_suppliers(engine: Engine) -> pd.DataFrame:
    suppliers = load_suppliers(engine)
    if "active" not in suppliers.columns:
        return suppliers
    return suppliers[suppliers["active"].fillna(True)].reset_index(drop=True)


def load_customers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("customers", con=engine)


def load_active_customers(engine: Engine) -> pd.DataFrame:
    customers = load_customers(engine)
    if "active" not in customers.columns:
        return customers
    return customers[customers["active"].fillna(True)].reset_index(drop=True)


def load_warehouses(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("warehouses", con=engine)


def load_plants(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("plants", con=engine)


def load_purchase_orders(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("purchase_orders", con=engine)


def load_sales_orders(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("sales_orders", con=engine)


def load_production_orders(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("production_orders", con=engine)


def load_inventory_transactions(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("inventory_transactions", con=engine)


def load_inventory_transaction_reference_ids(engine: Engine) -> set[str]:
    inventory_transactions = load_inventory_transactions(engine)
    if inventory_transactions.empty:
        return set()

    return set(inventory_transactions["reference_id"].dropna().astype(str))


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


def load_clean_completed_production_orders(engine: Engine) -> pd.DataFrame:
    production_orders = load_production_orders(engine)
    production_orders = dedupe_bronze_orders(production_orders, "production_order_id")
    return production_orders[
        production_orders["status"].isin(PRODUCTION_ORDER_OUTPUT_STATUSES)
    ].reset_index(drop=True)


def load_production_output(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("production_output", con=engine)


def load_clean_production_output(engine: Engine) -> pd.DataFrame:
    production_output = load_production_output(engine)
    production_output = dedupe_bronze_orders(production_output, "production_output_id")
    production_output = dedupe_bronze_orders(production_output, "production_order_id")

    completed_production_orders = load_clean_completed_production_orders(engine)
    if completed_production_orders.empty or production_output.empty:
        return pd.DataFrame(
            columns=[
                "production_output_id",
                "production_order_id",
                "input_material_id",
                "input_quantity",
                "output_material_id",
                "output_quantity",
                "end_date",
            ]
        )

    valid_order_ids = set(completed_production_orders["production_order_id"].astype(str))
    production_output = production_output[
        production_output["production_order_id"].astype(str).isin(valid_order_ids)
    ]
    order_dates = completed_production_orders[
        ["production_order_id", "end_date"]
    ].drop_duplicates(subset="production_order_id", keep="last")

    return (
        production_output.merge(order_dates, on="production_order_id", how="inner")
        .reset_index(drop=True)
    )
