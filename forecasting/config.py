"""Forecasting package configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ForecastConfig:
    """Runtime knobs for the local forecasting pipeline."""

    # Schema names in local Postgres (kept separate from public bronze tables)
    refined_schema: str = "forecast_refined"
    serve_schema: str = "forecast_serve"
    ml_schema: str = "forecast_ml"

    # Focus forecasting on high-volume finished goods
    top_materials_limit: int = 10

    # Evaluation / horizon
    test_months: int = 6
    forecast_horizon_months: int = 12

    # Prophet hyperparameters
    seasonality_mode: str = "multiplicative"
    yearly_seasonality: bool = True
    weekly_seasonality: bool = False
    daily_seasonality: bool = False
    changepoint_prior_scale: float = 0.1
    seasonality_prior_scale: float = 10.0

    # Machine downtime generation window (align with sales history)
    downtime_start_date: date = date(2021, 7, 1)
    downtime_end_date: date = date(2026, 7, 7)
    downtime_count: int = 1800
    downtime_seed: int = 42

    # Target column for material-level models
    target_column: str = "sales_quantity"

    # Exogenous regressors available at train time (future filled via seasonal lag)
    regressors: tuple[str, ...] = (
        "purchase_quantity",
        "production_output_quantity",
        "inventory_on_hand",
        "downtime_hours",
    )


DEFAULT_CONFIG = ForecastConfig()
