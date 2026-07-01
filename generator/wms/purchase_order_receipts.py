import pandas as pd
from sqlalchemy.engine import Engine

from generator.utils.db_export import write_dataframe
from generator.utils.master_data import (
    PURCHASE_ORDER_RECEIPT_STATUSES,
    load_goods_receipt_reference_ids,
    load_materials,
    load_warehouses,
)
from generator.utils.order_ids import resolve_next_id_start
from generator.wms.inventory import refresh_inventory_snapshot
from generator.wms.inventory_transactions import generate_goods_receipt_transactions
from generator.wms.warehouses import dedupe_bronze_orders


def _eligible_delivered_purchase_orders(purchase_orders: pd.DataFrame) -> pd.DataFrame:
    delivered = dedupe_bronze_orders(purchase_orders, "purchase_order_id")
    return delivered[
        delivered["status"].isin(PURCHASE_ORDER_RECEIPT_STATUSES)
    ].reset_index(drop=True)


def sync_goods_receipts_for_purchase_orders(
    purchase_orders: pd.DataFrame,
    engine: Engine,
) -> dict[str, int]:
    """Create goods receipts for new delivered POs and rebuild the inventory snapshot."""
    eligible = _eligible_delivered_purchase_orders(purchase_orders)
    existing_reference_ids = load_goods_receipt_reference_ids(engine)

    if not eligible.empty and existing_reference_ids:
        eligible = eligible[
            ~eligible["purchase_order_id"].astype(str).isin(existing_reference_ids)
        ].reset_index(drop=True)

    if eligible.empty:
        inventory_rows = refresh_inventory_snapshot(engine)
        return {
            "goods_receipts": 0,
            "inventory_transactions": 0,
            "inventory": inventory_rows,
        }

    materials = load_materials(engine)
    warehouses = load_warehouses(engine)
    id_start = resolve_next_id_start(
        engine, "inventory_transactions", "transaction_id", "IT"
    )
    transactions = generate_goods_receipt_transactions(
        eligible,
        materials,
        warehouses,
        id_start=id_start,
    )
    transaction_rows = write_dataframe(transactions, "inventory_transactions", engine)
    inventory_rows = refresh_inventory_snapshot(engine)

    return {
        "goods_receipts": len(transactions),
        "inventory_transactions": transaction_rows,
        "inventory": inventory_rows,
    }
