from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from generator.config.settings import WmsSettings
from generator.utils.csv_export import write_csv
from generator.utils.db_export import write_dataframe
from generator.wms.dates import parse_transaction_day
from generator.wms.inventory import generate_daily_inventory_snapshots
from generator.wms.simulator import DailyWmsBatch


def add_transaction_day(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty:
        return transactions.copy()

    enriched = transactions.copy()
    enriched["transaction_day"] = enriched["transaction_date"].map(parse_transaction_day)
    return enriched


def sort_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty:
        return transactions.copy()

    ordered = add_transaction_day(transactions)
    return ordered.sort_values(
        ["transaction_day", "transaction_date", "transaction_id"],
        na_position="last",
    ).reset_index(drop=True)


def iter_transactions_by_day(
    transactions: pd.DataFrame,
) -> Iterator[tuple[date, pd.DataFrame]]:
    if transactions.empty:
        return

    ordered = sort_transactions(transactions)
    for transaction_day, day_transactions in ordered.groupby("transaction_day", sort=True):
        if transaction_day is None or pd.isna(transaction_day):
            continue
        yield transaction_day, day_transactions.drop(columns=["transaction_day"]).reset_index(drop=True)


def _daily_transactions_path(output_dir: Path, transaction_day: date) -> Path:
    return (
        output_dir
        / "inventory_transactions"
        / f"inventory_transactions_{transaction_day.isoformat()}.csv"
    )


def _daily_inventory_path(output_dir: Path, snapshot_day: date) -> Path:
    return output_dir / "inventory" / f"inventory_{snapshot_day.isoformat()}.csv"


def export_all_daily_transaction_csvs(
    transactions: pd.DataFrame,
    wms_settings: WmsSettings,
) -> int:
    """Export one CSV per business day from the full transaction history."""
    if transactions.empty or not wms_settings.export_daily_csv:
        return 0

    days_written = 0
    for transaction_day, day_transactions in iter_transactions_by_day(transactions):
        write_csv(
            day_transactions,
            _daily_transactions_path(wms_settings.output_dir, transaction_day),
        )
        days_written += 1
    return days_written


def write_daily_inventory_transactions(
    transactions: pd.DataFrame,
    engine: Engine,
    wms_settings: WmsSettings,
) -> dict[str, int]:
    """Append new transactions grouped by business date and export one CSV per day."""
    if transactions.empty:
        return {"inventory_transactions": 0, "transaction_days": 0}

    ordered = sort_transactions(transactions)
    rows_written = 0
    days_written = 0

    for transaction_day, day_transactions in iter_transactions_by_day(ordered):
        day_rows = write_dataframe(day_transactions, "inventory_transactions", engine)
        rows_written += day_rows
        days_written += 1

        if wms_settings.export_daily_csv:
            write_csv(day_transactions, _daily_transactions_path(wms_settings.output_dir, transaction_day))

    return {
        "inventory_transactions": rows_written,
        "transaction_days": days_written,
    }


def write_daily_inventory_snapshots(
    transactions: pd.DataFrame,
    engine: Engine,
    wms_settings: WmsSettings,
) -> dict[str, int]:
    """Rebuild end-of-day inventory levels for every day in the transaction calendar."""
    snapshots = generate_daily_inventory_snapshots(transactions)
    if snapshots.empty:
        write_dataframe(
            pd.DataFrame(columns=["snapshot_date", "warehouse_id", "material_id", "quantity"]),
            "inventory",
            engine,
        )
        return {"inventory": 0, "inventory_days": 0}

    rows_written = write_dataframe(snapshots, "inventory", engine)
    days_written = 0

    if wms_settings.export_daily_csv:
        for snapshot_day, day_snapshot in snapshots.groupby("snapshot_date", sort=True):
            write_csv(day_snapshot, _daily_inventory_path(wms_settings.output_dir, snapshot_day))
            days_written += 1
    else:
        days_written = snapshots["snapshot_date"].nunique()

    return {
        "inventory": rows_written,
        "inventory_days": days_written,
    }


def publish_daily_batch(
    batch: DailyWmsBatch,
    engine: Engine,
    wms_settings: WmsSettings,
) -> int:
    if batch.transactions.empty:
        return 0

    rows_written = write_dataframe(batch.transactions, "inventory_transactions", engine)
    if wms_settings.export_daily_csv:
        write_csv(
            batch.transactions,
            _daily_transactions_path(wms_settings.output_dir, batch.transaction_day),
        )
    return rows_written


def refresh_daily_inventory(
    all_transactions: pd.DataFrame,
    engine: Engine,
    wms_settings: WmsSettings,
) -> dict[str, int]:
    return write_daily_inventory_snapshots(all_transactions, engine, wms_settings)
