from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

import pandas as pd

from generator.wms.dates import parse_transaction_day
from generator.wms.inventory import _apply_transaction, _snapshot_rows
from generator.wms.inventory_transactions import (
    _goods_receipt_rows,
    _production_transaction_rows,
    _sales_shipment_rows,
)
from generator.wms.warehouses import resolve_warehouse_ids


@dataclass(frozen=True)
class DailyWmsBatch:
    transaction_day: date
    transactions: pd.DataFrame
    inventory_snapshot: pd.DataFrame


def _orders_for_day(orders: pd.DataFrame, date_column: str, transaction_day: date) -> pd.DataFrame:
    if orders.empty:
        return orders.copy()

    mask = orders[date_column].map(parse_transaction_day) == transaction_day
    return orders.loc[mask].reset_index(drop=True)


def _production_output_for_day(
    production_output: pd.DataFrame,
    transaction_day: date,
) -> pd.DataFrame:
    if production_output.empty:
        return production_output.copy()

    mask = production_output["end_date"].map(parse_transaction_day) == transaction_day
    return production_output.loc[mask].reset_index(drop=True)


def _collect_transaction_days(
    purchase_orders: pd.DataFrame,
    sales_orders: pd.DataFrame,
    production_output: pd.DataFrame,
) -> list[date]:
    days: set[date] = set()

    for _, order in purchase_orders.iterrows():
        transaction_day = parse_transaction_day(order.get("expected_delivery_date"))
        if transaction_day is not None:
            days.add(transaction_day)

    for _, order in sales_orders.iterrows():
        transaction_day = parse_transaction_day(order.get("requested_delivery_date"))
        if transaction_day is not None:
            days.add(transaction_day)

    for _, record in production_output.iterrows():
        transaction_day = parse_transaction_day(record.get("end_date"))
        if transaction_day is not None:
            days.add(transaction_day)

    return sorted(days)


def iter_daily_wms_batches(
    purchase_orders: pd.DataFrame,
    sales_orders: pd.DataFrame,
    production_output: pd.DataFrame,
    materials: pd.DataFrame,
    warehouses: pd.DataFrame,
    *,
    id_start: int = 1,
    existing_reference_ids: set[str] | None = None,
    opening_balances: dict[tuple[str, str], int] | None = None,
) -> Iterator[DailyWmsBatch]:
    """Simulate WMS one calendar day at a time in chronological order."""
    existing_reference_ids = existing_reference_ids or set()
    raw_materials_warehouse_id, finished_goods_warehouse_ids = resolve_warehouse_ids(warehouses)
    balances = dict(opening_balances or {})
    sequence = id_start

    for transaction_day in _collect_transaction_days(
        purchase_orders, sales_orders, production_output
    ):
        day_purchase_orders = _orders_for_day(
            purchase_orders, "expected_delivery_date", transaction_day
        )
        day_sales_orders = _orders_for_day(
            sales_orders, "requested_delivery_date", transaction_day
        )
        day_production_output = _production_output_for_day(production_output, transaction_day)

        goods_receipt_rows = _goods_receipt_rows(
            day_purchase_orders,
            materials,
            raw_materials_warehouse_id,
            id_start=sequence,
        )
        sequence += len(goods_receipt_rows)

        sales_shipment_rows = _sales_shipment_rows(
            day_sales_orders,
            materials,
            finished_goods_warehouse_ids,
            id_start=sequence,
        )
        sequence += len(sales_shipment_rows)

        production_rows = _production_transaction_rows(
            day_production_output,
            materials,
            raw_materials_warehouse_id,
            finished_goods_warehouse_ids,
            id_start=sequence,
        )
        sequence += len(production_rows)

        day_rows = goods_receipt_rows + sales_shipment_rows + production_rows
        if not day_rows:
            continue

        transactions = pd.DataFrame(day_rows)
        if existing_reference_ids:
            transactions = transactions[
                ~transactions["reference_id"].astype(str).isin(existing_reference_ids)
            ].reset_index(drop=True)

        if transactions.empty:
            continue

        for _, transaction in transactions.iterrows():
            _apply_transaction(
                balances,
                warehouse_id=str(transaction["warehouse_id"]),
                material_id=str(transaction["material_id"]),
                transaction_type=str(transaction["transaction_type"]),
                quantity=int(transaction["quantity"]),
            )

        inventory_snapshot = pd.DataFrame(_snapshot_rows(balances, transaction_day))
        yield DailyWmsBatch(
            transaction_day=transaction_day,
            transactions=transactions,
            inventory_snapshot=inventory_snapshot,
        )


def simulate_daily_wms_batches(
    purchase_orders: pd.DataFrame,
    sales_orders: pd.DataFrame,
    production_output: pd.DataFrame,
    materials: pd.DataFrame,
    warehouses: pd.DataFrame,
    *,
    id_start: int = 1,
    existing_reference_ids: set[str] | None = None,
    opening_balances: dict[tuple[str, str], int] | None = None,
) -> list[DailyWmsBatch]:
    return list(
        iter_daily_wms_batches(
            purchase_orders,
            sales_orders,
            production_output,
            materials,
            warehouses,
            id_start=id_start,
            existing_reference_ids=existing_reference_ids,
            opening_balances=opening_balances,
        )
    )
