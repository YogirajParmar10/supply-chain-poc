from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy.engine import Engine

from generator.config.settings import GeneratorConfig, WmsSettings
from generator.utils.master_data import load_inventory_transactions
from generator.utils.order_ids import resolve_next_id_start
from generator.wms.daily import (
    export_all_daily_transaction_csvs,
    publish_daily_batch,
    refresh_daily_inventory,
)
from generator.wms.inventory import compute_balances_through_day, generate_daily_inventory_snapshots
from generator.wms.simulator import iter_daily_wms_batches


def publish_wms_from_orders(
    purchase_orders: pd.DataFrame,
    sales_orders: pd.DataFrame,
    production_output: pd.DataFrame,
    materials: pd.DataFrame,
    warehouses: pd.DataFrame,
    engine: Engine,
    *,
    wms_settings: WmsSettings | None = None,
    existing_reference_ids: set[str] | None = None,
) -> dict[str, int]:
    """Simulate and publish WMS day by day, then rebuild the full daily inventory calendar."""
    settings = wms_settings or WmsSettings()
    existing_reference_ids = existing_reference_ids or set()
    prior_transactions = load_inventory_transactions(engine)

    id_start = resolve_next_id_start(
        engine, "inventory_transactions", "transaction_id", "IT"
    )
    opening_balances = compute_balances_through_day(prior_transactions)

    transaction_rows = 0
    transaction_days = 0
    goods_receipts = 0
    sales_shipments = 0
    production_consumptions = 0
    production_receipts = 0

    for batch in iter_daily_wms_batches(
        purchase_orders,
        sales_orders,
        production_output,
        materials,
        warehouses,
        id_start=id_start,
        existing_reference_ids=existing_reference_ids,
        opening_balances=opening_balances,
    ):
        day_rows = publish_daily_batch(batch, engine, settings)
        transaction_rows += day_rows
        transaction_days += 1
        goods_receipts += len(
            batch.transactions[batch.transactions["transaction_type"] == "GOODS_RECEIPT"]
        )
        sales_shipments += len(
            batch.transactions[batch.transactions["transaction_type"] == "SALES_SHIPMENT"]
        )
        production_consumptions += len(
            batch.transactions[
                batch.transactions["transaction_type"] == "PRODUCTION_CONSUMPTION"
            ]
        )
        production_receipts += len(
            batch.transactions[batch.transactions["transaction_type"] == "PRODUCTION_RECEIPT"]
        )
        print(
            f"  {batch.transaction_day.isoformat()}: "
            f"{day_rows} transactions, "
            f"{len(batch.inventory_snapshot)} inventory positions"
        )

    all_transactions = load_inventory_transactions(engine)
    inventory_stats = refresh_daily_inventory(all_transactions, engine, settings)
    transaction_csv_days = export_all_daily_transaction_csvs(all_transactions, settings)

    return {
        "inventory_transactions": transaction_rows,
        "transaction_days": transaction_days,
        "transaction_csv_days": transaction_csv_days,
        "goods_receipts": goods_receipts,
        "sales_shipments": sales_shipments,
        "production_consumptions": production_consumptions,
        "production_receipts": production_receipts,
        "inventory": inventory_stats.get("inventory", 0),
        "inventory_days": inventory_stats.get("inventory_days", 0),
    }


def publish_wms_data(
    new_transactions: pd.DataFrame,
    engine: Engine,
    *,
    wms_settings: WmsSettings | None = None,
) -> dict[str, int]:
    """Backward-compatible publish path when callers already built a transaction DataFrame."""
    settings = wms_settings or WmsSettings()
    from generator.wms.daily import write_daily_inventory_transactions

    transaction_stats = write_daily_inventory_transactions(new_transactions, engine, settings)
    all_transactions = load_inventory_transactions(engine)
    inventory_stats = refresh_daily_inventory(all_transactions, engine, settings)
    transaction_csv_days = export_all_daily_transaction_csvs(all_transactions, settings)

    return {
        **transaction_stats,
        **inventory_stats,
        "transaction_csv_days": transaction_csv_days,
    }


def publish_wms_from_orders_config(
    purchase_orders: pd.DataFrame,
    sales_orders: pd.DataFrame,
    production_output: pd.DataFrame,
    materials: pd.DataFrame,
    warehouses: pd.DataFrame,
    engine: Engine,
    config: GeneratorConfig | None = None,
    *,
    existing_reference_ids: set[str] | None = None,
) -> dict[str, int]:
    config = config or GeneratorConfig()
    return publish_wms_from_orders(
        purchase_orders,
        sales_orders,
        production_output,
        materials,
        warehouses,
        engine,
        wms_settings=config.wms,
        existing_reference_ids=existing_reference_ids,
    )


def publish_wms_data_from_config(
    new_transactions: pd.DataFrame,
    engine: Engine,
    config: GeneratorConfig | None = None,
) -> dict[str, int]:
    config = config or GeneratorConfig()
    return publish_wms_data(new_transactions, engine, wms_settings=config.wms)


def preview_daily_calendar(transactions: pd.DataFrame) -> tuple[date | None, date | None, int]:
    snapshots = generate_daily_inventory_snapshots(transactions)
    if snapshots.empty:
        return None, None, 0
    return (
        snapshots["snapshot_date"].min(),
        snapshots["snapshot_date"].max(),
        snapshots["snapshot_date"].nunique(),
    )
