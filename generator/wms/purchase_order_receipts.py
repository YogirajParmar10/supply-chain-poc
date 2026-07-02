import pandas as pd
from sqlalchemy.engine import Engine

from generator.config.settings import GeneratorConfig
from generator.utils.master_data import (
    PURCHASE_ORDER_RECEIPT_STATUSES,
    load_goods_receipt_reference_ids,
    load_materials,
    load_sales_orders,
    load_warehouses,
)
from generator.wms.publisher import publish_wms_from_orders_config
from generator.wms.warehouses import dedupe_bronze_orders


def _eligible_delivered_purchase_orders(purchase_orders: pd.DataFrame) -> pd.DataFrame:
    delivered = dedupe_bronze_orders(purchase_orders, "purchase_order_id")
    return delivered[
        delivered["status"].isin(PURCHASE_ORDER_RECEIPT_STATUSES)
    ].reset_index(drop=True)


def sync_goods_receipts_for_purchase_orders(
    purchase_orders: pd.DataFrame,
    engine: Engine,
    config: GeneratorConfig | None = None,
) -> dict[str, int]:
    """Create goods receipts for new delivered POs day by day and rebuild daily inventory."""
    config = config or GeneratorConfig()
    eligible = _eligible_delivered_purchase_orders(purchase_orders)
    existing_reference_ids = load_goods_receipt_reference_ids(engine)

    if not eligible.empty and existing_reference_ids:
        eligible = eligible[
            ~eligible["purchase_order_id"].astype(str).isin(existing_reference_ids)
        ].reset_index(drop=True)

    materials = load_materials(engine)
    warehouses = load_warehouses(engine)
    empty_sales_orders = load_sales_orders(engine).iloc[0:0]

    publish_stats = publish_wms_from_orders_config(
        eligible,
        empty_sales_orders,
        materials,
        warehouses,
        engine,
        config,
        existing_reference_ids=existing_reference_ids,
    )

    return {
        "goods_receipts": publish_stats.get("goods_receipts", 0),
        **publish_stats,
    }
