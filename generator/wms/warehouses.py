import hashlib

import pandas as pd


def dedupe_bronze_orders(orders: pd.DataFrame, id_column: str) -> pd.DataFrame:
    if orders.empty:
        return orders

    if "bronze_row_id" in orders.columns:
        return (
            orders.sort_values("bronze_row_id")
            .drop_duplicates(subset=id_column, keep="last")
            .reset_index(drop=True)
        )

    return orders.drop_duplicates(subset=id_column, keep="last").reset_index(drop=True)


def resolve_warehouse_ids(warehouses: pd.DataFrame) -> tuple[str, list[str]]:
    raw_mask = warehouses["warehouse_name"].str.contains("Raw Materials", case=False, na=False)
    raw_warehouses = warehouses.loc[raw_mask, "warehouse_id"].tolist()
    finished_goods_warehouses = warehouses.loc[~raw_mask, "warehouse_id"].tolist()

    if not raw_warehouses:
        raise ValueError("No raw materials warehouse found in warehouses master data")
    if not finished_goods_warehouses:
        raise ValueError("No finished goods warehouse found in warehouses master data")

    return raw_warehouses[0], finished_goods_warehouses


def select_finished_goods_warehouse(
    sales_order_id: str,
    finished_goods_warehouse_ids: list[str],
) -> str:
    digest = hashlib.md5(sales_order_id.encode(), usedforsecurity=False).hexdigest()
    index = int(digest, 16) % len(finished_goods_warehouse_ids)
    return finished_goods_warehouse_ids[index]
