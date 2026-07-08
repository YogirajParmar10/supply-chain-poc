from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

import pandas as pd

from generator.wms.dates import date_range, parse_transaction_day
from generator.wms.inventory_transactions import (
    ISSUE_TRANSACTION_TYPES,
    RECEIPT_TRANSACTION_TYPES,
)


def _positive_quantity(value: object) -> int:
    try:
        quantity = int(float(value))
    except (TypeError, ValueError):
        return 0
    return quantity


def _apply_transaction(
    balances: dict[tuple[str, str], int],
    *,
    warehouse_id: str,
    material_id: str,
    transaction_type: str,
    quantity: int,
) -> None:
    if quantity <= 0:
        return

    key = (warehouse_id, material_id)
    if transaction_type in RECEIPT_TRANSACTION_TYPES:
        balances[key] = balances.get(key, 0) + quantity
    elif transaction_type in ISSUE_TRANSACTION_TYPES:
        balances[key] = balances.get(key, 0) - quantity


def _snapshot_rows(
    balances: dict[tuple[str, str], int],
    snapshot_day: date,
) -> list[dict[str, object]]:
    return [
        {
            "snapshot_date": snapshot_day,
            "warehouse_id": warehouse_id,
            "material_id": material_id,
            "quantity": quantity,
        }
        for (warehouse_id, material_id), quantity in sorted(balances.items())
        if quantity > 0
    ]


def compute_balances_through_day(
    inventory_transactions: pd.DataFrame,
    *,
    through_day: date | None = None,
) -> dict[tuple[str, str], int]:
    balances: dict[tuple[str, str], int] = {}

    for _, transaction in inventory_transactions.iterrows():
        transaction_day = parse_transaction_day(transaction.get("transaction_date"))
        if transaction_day is None:
            continue
        if through_day is not None and transaction_day > through_day:
            continue

        warehouse_id = transaction.get("warehouse_id")
        material_id = transaction.get("material_id")
        transaction_type = transaction.get("transaction_type")
        quantity = _positive_quantity(transaction.get("quantity"))

        if not warehouse_id or not material_id or not transaction_type:
            continue

        _apply_transaction(
            balances,
            warehouse_id=str(warehouse_id),
            material_id=str(material_id),
            transaction_type=str(transaction_type),
            quantity=quantity,
        )

    return balances


def generate_inventory(inventory_transactions: pd.DataFrame) -> pd.DataFrame:
    """Return the latest end-of-day inventory snapshot."""
    daily_snapshots = generate_daily_inventory_snapshots(inventory_transactions)
    if daily_snapshots.empty:
        return pd.DataFrame(columns=["warehouse_id", "material_id", "quantity"])

    latest_day = daily_snapshots["snapshot_date"].max()
    latest_snapshot = daily_snapshots[daily_snapshots["snapshot_date"] == latest_day].copy()
    return latest_snapshot.drop(columns=["snapshot_date"]).reset_index(drop=True)


def generate_daily_inventory_snapshots(inventory_transactions: pd.DataFrame) -> pd.DataFrame:
    if inventory_transactions.empty:
        return pd.DataFrame(columns=["snapshot_date", "warehouse_id", "material_id", "quantity"])

    transactions_by_day: dict[date, list[dict[str, object]]] = defaultdict(list)
    transaction_days: list[date] = []

    for _, transaction in inventory_transactions.iterrows():
        transaction_day = parse_transaction_day(transaction.get("transaction_date"))
        if transaction_day is None:
            continue

        warehouse_id = transaction.get("warehouse_id")
        material_id = transaction.get("material_id")
        transaction_type = transaction.get("transaction_type")
        quantity = _positive_quantity(transaction.get("quantity"))

        if not warehouse_id or not material_id or not transaction_type:
            continue

        transactions_by_day[transaction_day].append(
            {
                "warehouse_id": str(warehouse_id),
                "material_id": str(material_id),
                "transaction_type": str(transaction_type),
                "quantity": quantity,
            }
        )
        transaction_days.append(transaction_day)

    if not transaction_days:
        return pd.DataFrame(columns=["snapshot_date", "warehouse_id", "material_id", "quantity"])

    balances: dict[tuple[str, str], int] = {}
    rows: list[dict[str, object]] = []

    for snapshot_day in date_range(min(transaction_days), max(transaction_days)):
        for transaction in transactions_by_day.get(snapshot_day, []):
            _apply_transaction(
                balances,
                warehouse_id=transaction["warehouse_id"],
                material_id=transaction["material_id"],
                transaction_type=transaction["transaction_type"],
                quantity=transaction["quantity"],
            )
        rows.extend(_snapshot_rows(balances, snapshot_day))

    return pd.DataFrame(rows)
