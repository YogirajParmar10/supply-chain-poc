"""Lightweight exploration helpers for local forecast outputs.

Usage (from repo root, after running the pipeline):

    python forecasting/notebooks/explore_forecasts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from forecasting.db import get_forecast_engine


def main() -> None:
    engine = get_forecast_engine()

    runs = pd.read_sql(
        """
        SELECT run_id, run_name, as_of_date, grain, target_column, created_at
        FROM forecast_ml.forecast_runs
        ORDER BY run_id DESC
        LIMIT 10
        """,
        engine,
    )
    print("=== Recent runs ===")
    print(runs.to_string(index=False))

    if runs.empty:
        print("No runs yet. Execute: python -m forecasting.pipelines.run_all")
        return

    latest_company = runs.loc[runs["grain"] == "company", "run_id"]
    if not latest_company.empty:
        run_id = int(latest_company.iloc[0])
        forecast = pd.read_sql(
            f"""
            SELECT year_month, yhat, yhat_lower, yhat_upper
            FROM forecast_ml.sales_forecast_monthly
            WHERE run_id = {run_id}
            ORDER BY forecast_month
            """,
            engine,
        )
        metrics = pd.read_sql(
            f"""
            SELECT metric_name, metric_value
            FROM forecast_ml.forecast_backtest
            WHERE run_id = {run_id}
            """,
            engine,
        )
        print(f"\n=== Company forecast (run_id={run_id}) ===")
        print(metrics.to_string(index=False))
        print(forecast.round(0).to_string(index=False))

    latest_material = runs.loc[runs["grain"] == "material", "run_id"]
    if not latest_material.empty:
        run_id = int(latest_material.iloc[0])
        metrics = pd.read_sql(
            f"""
            SELECT grain_id, metric_name, ROUND(metric_value::numeric, 2) AS value
            FROM forecast_ml.forecast_backtest
            WHERE run_id = {run_id}
              AND metric_name IN ('mape', 'wmape')
            ORDER BY grain_id, metric_name
            """,
            engine,
        )
        print(f"\n=== Material backtest (run_id={run_id}) ===")
        print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
