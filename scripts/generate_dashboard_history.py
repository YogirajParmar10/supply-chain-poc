#!/usr/bin/env python3
"""Generate twelve months of FMCG dashboard data into PostgreSQL."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.config.settings import GeneratorConfig, HistoryBackfillSettings, NoiseSettings
from generator.history.monthly import generate_history_month, iter_history_months
from generator.main import (
    generate_master_data,
    generate_production_order_data,
    generate_production_output_data,
    generate_purchase_order_data,
    generate_sales_order_data,
)
from generator.utils.db import get_engine
from generator.utils.db_export import truncate_transactional_tables
from generator.utils.migrations import ensure_migrations_applied
from generator.wms.publisher import preview_daily_calendar, rebuild_wms_from_scratch
from generator.utils.master_data import load_inventory_transactions


def build_config(args: argparse.Namespace) -> GeneratorConfig:
    history = HistoryBackfillSettings(
        month_count=args.months,
        start_month=date.fromisoformat(args.start_month),
        cap_end_date=date.fromisoformat(args.end_date) if args.end_date else None,
    )
    return GeneratorConfig(
        seed=args.seed,
        history=history,
        noise=NoiseSettings(enabled=not args.clean),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate twelve months of realistic FMCG dashboard data."
    )
    parser.add_argument(
        "--reset-transactional",
        action="store_true",
        help="Truncate orders, production, and WMS tables before generating history.",
    )
    parser.add_argument(
        "--start-month",
        default="2025-08-01",
        help="First calendar month to generate (YYYY-MM-DD, day ignored).",
    )
    parser.add_argument(
        "--end-date",
        default=date.today().isoformat(),
        help="Cap the final month on this calendar date.",
    )
    parser.add_argument("--months", type=int, default=12, help="Number of months to generate.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for master data.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Disable bronze noise so dashboard metrics stay clean.",
    )
    args = parser.parse_args()

    config = build_config(args)
    engine = get_engine()

    applied_migrations = ensure_migrations_applied()
    if applied_migrations:
        print("Applied pending database migrations:")
        for migration_name in applied_migrations:
            print(f"  - {migration_name}")

    if args.reset_transactional:
        print("Resetting transactional tables...")
        truncate_transactional_tables(engine)

    print("Updating master data (customers, suppliers, materials, plants, warehouses)...")
    master_rows = generate_master_data(config)
    for table_name, row_count in master_rows.items():
        print(f"  - {table_name}: {row_count} rows")

    history_months = iter_history_months(config.history)
    print(
        f"Generating {len(history_months)} months of orders "
        f"from {history_months[0].start_date} to {history_months[-1].end_date}..."
    )

    total_purchase_orders = 0
    total_sales_orders = 0
    total_production_orders = 0

    for history_month in history_months:
        month_config = generate_history_month(history_month, config)
        print(
            f"  {history_month.year}-{history_month.month:02d}: "
            f"PO={history_month.purchase_order_count}, "
            f"SO={history_month.sales_order_count}, "
            f"PR={history_month.production_order_count}"
        )
        total_purchase_orders += generate_purchase_order_data(month_config)
        total_sales_orders += generate_sales_order_data(month_config)
        total_production_orders += generate_production_order_data(month_config)

    production_output_rows = generate_production_output_data(config)

    print("Rebuilding WMS inventory transactions and daily snapshots...")
    wms_stats = rebuild_wms_from_scratch(engine, config)
    preview_start, preview_end, preview_days = preview_daily_calendar(
        load_inventory_transactions(engine)
    )

    print("")
    print(f"Generated dashboard history for {config.company_name}")
    print(f"  - purchase_orders: {total_purchase_orders} rows")
    print(f"  - sales_orders: {total_sales_orders} rows")
    print(f"  - production_orders: {total_production_orders} rows")
    print(f"  - production_output: {production_output_rows} rows")
    print(f"  - inventory_transactions: {wms_stats.get('inventory_transactions', 0)} rows")
    print(f"  - transaction days: {wms_stats.get('transaction_days', 0)}")
    print(f"  - inventory snapshot rows: {wms_stats.get('inventory', 0)} rows")
    print(f"  - inventory days: {wms_stats.get('inventory_days', 0)}")
    if preview_start and preview_end:
        print(
            f"  - inventory calendar: {preview_start.isoformat()} to "
            f"{preview_end.isoformat()} ({preview_days} days)"
        )


if __name__ == "__main__":
    main()
