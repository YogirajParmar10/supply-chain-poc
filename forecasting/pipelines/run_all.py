"""CLI: build local gold features and train Prophet forecasts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python -m forecasting.pipelines.run_all` from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from forecasting.config import DEFAULT_CONFIG, ForecastConfig
from forecasting.db import apply_forecast_sql, get_forecast_engine
from forecasting.features.build import build_all_features
from forecasting.features.downtime import generate_forecast_downtime
from forecasting.models.prophet_forecast import run_forecast_models


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build forecast gold tables and train Prophet models in local Postgres."
    )
    parser.add_argument(
        "--skip-downtime",
        action="store_true",
        help="Do not generate machine_downtime (use existing rows).",
    )
    parser.add_argument(
        "--force-downtime",
        action="store_true",
        help="Truncate and regenerate machine_downtime history.",
    )
    parser.add_argument(
        "--skip-train",
        action="store_true",
        help="Only apply SQL + build features; skip model training.",
    )
    parser.add_argument(
        "--top-materials",
        type=int,
        default=DEFAULT_CONFIG.top_materials_limit,
        help="Number of top finished goods to forecast (default: 10).",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=DEFAULT_CONFIG.forecast_horizon_months,
        help="Forecast horizon in months (default: 12).",
    )
    parser.add_argument(
        "--test-months",
        type=int,
        default=DEFAULT_CONFIG.test_months,
        help="Holdout months for backtest (default: 6).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = ForecastConfig(
        top_materials_limit=args.top_materials,
        forecast_horizon_months=args.horizon,
        test_months=args.test_months,
    )

    engine = get_forecast_engine()
    print("=== 1) Ensure machine_downtime ===")
    if args.skip_downtime:
        from forecasting.features.downtime import ensure_machine_downtime_table

        ensure_machine_downtime_table(engine)
        print("Skipped downtime generation")
    else:
        generate_forecast_downtime(engine, config, force=args.force_downtime)

    print("\n=== 2) Apply forecasting SQL (schemas / views / tables) ===")
    applied = apply_forecast_sql(engine)
    for name in applied:
        print(f"  applied {name}")

    print("\n=== 3) Build gold feature tables ===")
    counts = build_all_features(engine, config)
    for table, count in counts.items():
        print(f"  forecast_serve.{table}: {count} rows")

    if args.skip_train:
        print("\nSkipped model training (--skip-train)")
        return 0

    print("\n=== 4) Train Prophet models + write forecasts ===")
    results = run_forecast_models(engine, config)
    company = results["company"]
    print(
        f"\nCompany run_id={company['run_id']}  "
        f"MAPE={company['metrics']['mape']:.1f}%  "
        f"forecast_rows={company['forecast_rows']}"
    )
    material = results["materials"]
    print(
        f"Material run_id={material['run_id']}  "
        f"skus_trained={len(material['materials'])}"
    )
    print("\nDone. Query forecast_ml.sales_forecast_monthly for outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
