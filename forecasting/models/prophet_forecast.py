"""Prophet forecasting with exogenous regressors (inventory, downtime, procurement)."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from prophet import Prophet
from sqlalchemy import text
from sqlalchemy.engine import Engine

from forecasting.config import ForecastConfig, DEFAULT_CONFIG
from forecasting.db import get_forecast_engine


def _prophet_params(
    config: ForecastConfig,
    *,
    seasonality_mode: str | None = None,
) -> dict[str, Any]:
    return {
        "seasonality_mode": seasonality_mode or config.seasonality_mode,
        "yearly_seasonality": config.yearly_seasonality,
        "weekly_seasonality": config.weekly_seasonality,
        "daily_seasonality": config.daily_seasonality,
        "changepoint_prior_scale": config.changepoint_prior_scale,
        "seasonality_prior_scale": config.seasonality_prior_scale,
    }


def _metrics(actuals: np.ndarray, preds: np.ndarray) -> dict[str, float]:
    actuals = np.asarray(actuals, dtype=float)
    preds = np.asarray(preds, dtype=float)
    err = actuals - preds
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    nonzero = np.abs(actuals) > 1e-9
    if nonzero.any():
        mape = float(np.mean(np.abs(err[nonzero] / actuals[nonzero])) * 100)
        wmape = float(np.sum(np.abs(err[nonzero])) / np.sum(np.abs(actuals[nonzero])) * 100)
    else:
        mape = float("nan")
        wmape = float("nan")
    return {"mae": mae, "rmse": rmse, "mape": mape, "wmape": wmape}


def _fill_future_regressors(
    history: pd.DataFrame,
    future: pd.DataFrame,
    regressors: tuple[str, ...],
) -> pd.DataFrame:
    """
    For future months, fill regressors with same-month-last-year values when available,
    else trailing 3-month mean.
    """
    out = future.copy()
    hist = history.sort_values("ds").copy()
    for col in regressors:
        if col not in hist.columns:
            out[col] = 0.0
            continue
        hist_map = hist.set_index("ds")[col]
        values: list[float] = []
        for ds in out["ds"]:
            if ds in hist_map.index:
                values.append(float(hist_map.loc[ds]))
                continue
            lag_year = ds - pd.DateOffset(years=1)
            if lag_year in hist_map.index:
                values.append(float(hist_map.loc[lag_year]))
                continue
            trailing = hist_map[hist_map.index < ds].tail(3)
            values.append(float(trailing.mean()) if len(trailing) else 0.0)
        out[col] = values
    return out


def _active_regressors(train_df: pd.DataFrame, regressors: tuple[str, ...]) -> list[str]:
    """Drop constant / missing regressors (e.g. purchase_qty on finished goods)."""
    active: list[str] = []
    for col in regressors:
        if col not in train_df.columns:
            continue
        series = train_df[col].astype(float)
        if series.nunique(dropna=True) <= 1:
            continue
        if float(series.std(skipna=True) or 0.0) <= 1e-9:
            continue
        active.append(col)
    return active


def _fit_prophet(
    train_df: pd.DataFrame,
    config: ForecastConfig,
    regressors: tuple[str, ...],
    *,
    seasonality_mode: str | None = None,
) -> tuple[Prophet, list[str]]:
    active = _active_regressors(train_df, regressors)
    model = Prophet(**_prophet_params(config, seasonality_mode=seasonality_mode))
    for col in active:
        model.add_regressor(col)
    model.fit(train_df[["ds", "y", *active]])
    return model, active


def _prepare_series(
    df: pd.DataFrame,
    target: str,
    regressors: tuple[str, ...],
) -> pd.DataFrame:
    frame = df.copy()
    frame["ds"] = pd.to_datetime(frame["month_start_date"])
    frame["y"] = frame[target].astype(float)
    for col in regressors:
        if col not in frame.columns:
            frame[col] = 0.0
        frame[col] = frame[col].astype(float).fillna(0.0)
    return frame.sort_values("ds").reset_index(drop=True)


def _predict_horizon(
    model: Prophet,
    history: pd.DataFrame,
    periods: int,
    regressors: list[str],
) -> pd.DataFrame:
    future = model.make_future_dataframe(periods=periods, freq="MS")
    if regressors:
        future = _fill_future_regressors(history, future, tuple(regressors))
    forecast = model.predict(future)
    return forecast


def load_company_features(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM forecast_serve.company_forecast_features_monthly ORDER BY month_start_date",
        engine,
        parse_dates=["month_start_date"],
    )


def load_material_features(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM forecast_serve.forecast_features_monthly ORDER BY material_id, month_start_date",
        engine,
        parse_dates=["month_start_date"],
    )


def _insert_run(
    engine: Engine,
    *,
    run_name: str,
    as_of_date: date,
    grain: str,
    config: ForecastConfig,
) -> int:
    params = _prophet_params(config)
    params["regressors"] = list(config.regressors)
    with engine.begin() as conn:
        run_id = conn.execute(
            text(
                """
                INSERT INTO forecast_ml.forecast_runs (
                    run_name, as_of_date, grain, target_column, model_name,
                    horizon_months, test_months, top_materials_limit, params_json
                )
                VALUES (
                    :run_name, :as_of_date, :grain, :target_column, :model_name,
                    :horizon_months, :test_months, :top_materials_limit,
                    CAST(:params_json AS jsonb)
                )
                RETURNING run_id
                """
            ),
            {
                "run_name": run_name,
                "as_of_date": as_of_date,
                "grain": grain,
                "target_column": config.target_column,
                "model_name": "prophet_with_regressors",
                "horizon_months": config.forecast_horizon_months,
                "test_months": config.test_months,
                "top_materials_limit": config.top_materials_limit,
                "params_json": json.dumps(params),
            },
        ).scalar_one()
    return int(run_id)


def _write_backtest(
    engine: Engine,
    run_id: int,
    grain_id: str,
    metrics: dict[str, float],
    detail: pd.DataFrame,
) -> None:
    with engine.begin() as conn:
        for name, value in metrics.items():
            if value != value:  # NaN
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO forecast_ml.forecast_backtest (run_id, grain_id, metric_name, metric_value)
                    VALUES (:run_id, :grain_id, :metric_name, :metric_value)
                    """
                ),
                {
                    "run_id": run_id,
                    "grain_id": grain_id,
                    "metric_name": name,
                    "metric_value": float(value),
                },
            )
        for row in detail.itertuples(index=False):
            conn.execute(
                text(
                    """
                    INSERT INTO forecast_ml.forecast_backtest_detail (
                        run_id, grain_id, forecast_month, actual, predicted, error
                    )
                    VALUES (
                        :run_id, :grain_id, :forecast_month, :actual, :predicted, :error
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "grain_id": grain_id,
                    "forecast_month": row.ds.date() if hasattr(row.ds, "date") else row.ds,
                    "actual": float(row.actual),
                    "predicted": float(row.predicted),
                    "error": float(row.error),
                },
            )


def _write_forecast(
    engine: Engine,
    run_id: int,
    as_of_date: date,
    grain: str,
    grain_id: str,
    forecast: pd.DataFrame,
    cutoff: pd.Timestamp,
    model_name: str,
) -> int:
    next_rows = forecast[forecast["ds"] > cutoff][
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].copy()
    with engine.begin() as conn:
        for row in next_rows.itertuples(index=False):
            conn.execute(
                text(
                    """
                    INSERT INTO forecast_ml.sales_forecast_monthly (
                        run_id, as_of_date, grain, grain_id, forecast_month, year_month,
                        yhat, yhat_lower, yhat_upper, model_name
                    )
                    VALUES (
                        :run_id, :as_of_date, :grain, :grain_id, :forecast_month, :year_month,
                        :yhat, :yhat_lower, :yhat_upper, :model_name
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "as_of_date": as_of_date,
                    "grain": grain,
                    "grain_id": grain_id,
                    "forecast_month": row.ds.date(),
                    "year_month": row.ds.strftime("%Y-%m"),
                    "yhat": float(row.yhat),
                    "yhat_lower": float(row.yhat_lower),
                    "yhat_upper": float(row.yhat_upper),
                    "model_name": model_name,
                },
            )
    return len(next_rows)


def _train_one_series(
    series: pd.DataFrame,
    *,
    grain_id: str,
    config: ForecastConfig,
    seasonality_mode: str | None = None,
) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Holdout evaluate, then refit on full history and forecast horizon."""
    prepared = _prepare_series(series, config.target_column, config.regressors)
    if len(prepared) <= config.test_months + 12:
        raise ValueError(
            f"{grain_id}: need more than {config.test_months + 12} months, got {len(prepared)}"
        )

    # Clip tiny negatives from model noise; keep zeros for intermittent demand
    prepared["y"] = prepared["y"].clip(lower=0.0)

    train = prepared.iloc[: -config.test_months].copy()
    test = prepared.iloc[-config.test_months :].copy()

    model_cv, active_cv = _fit_prophet(
        train, config, config.regressors, seasonality_mode=seasonality_mode
    )
    future_cv = _predict_horizon(model_cv, train, config.test_months, active_cv)
    preds = future_cv.set_index("ds")["yhat"].reindex(test["ds"].values).clip(lower=0.0)
    actuals = test.set_index("ds")["y"]
    metrics = _metrics(actuals.values, preds.values)

    detail = pd.DataFrame(
        {
            "ds": test["ds"].values,
            "actual": actuals.values,
            "predicted": preds.values,
            "error": actuals.values - preds.values,
        }
    )

    model_full, active_full = _fit_prophet(
        prepared, config, config.regressors, seasonality_mode=seasonality_mode
    )
    forecast = _predict_horizon(
        model_full, prepared, config.forecast_horizon_months, active_full
    )
    for col in ("yhat", "yhat_lower", "yhat_upper"):
        forecast[col] = forecast[col].clip(lower=0.0)
    cutoff = prepared["ds"].max()
    return metrics, detail, forecast, cutoff


def run_company_forecast(
    engine: Engine,
    config: ForecastConfig = DEFAULT_CONFIG,
    *,
    run_name: str | None = None,
) -> dict[str, Any]:
    company = load_company_features(engine)
    if company.empty:
        raise RuntimeError("company_forecast_features_monthly is empty; build features first")

    # Company target: sales_quantity (same name as material target)
    as_of = company["month_start_date"].max()
    if isinstance(as_of, datetime):
        as_of = as_of.date()
    elif hasattr(as_of, "date") and not isinstance(as_of, date):
        as_of = as_of.date()

    run_id = _insert_run(
        engine,
        run_name=run_name or f"company_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        as_of_date=as_of,
        grain="company",
        config=config,
    )

    if config.target_column not in company.columns:
        raise RuntimeError(
            f"Target '{config.target_column}' missing from company features. "
            f"Columns: {list(company.columns)}"
        )

    metrics, detail, forecast, cutoff = _train_one_series(
        company,
        grain_id="COMPANY",
        config=config,
    )
    _write_backtest(engine, run_id, "COMPANY", metrics, detail)
    n_forecast = _write_forecast(
        engine,
        run_id,
        as_of,
        "company",
        "COMPANY",
        forecast,
        cutoff,
        "prophet_with_regressors",
    )
    return {
        "run_id": run_id,
        "grain": "company",
        "metrics": metrics,
        "forecast_rows": n_forecast,
    }


def run_material_forecasts(
    engine: Engine,
    config: ForecastConfig = DEFAULT_CONFIG,
    *,
    run_name: str | None = None,
) -> dict[str, Any]:
    features = load_material_features(engine)
    if features.empty:
        raise RuntimeError("forecast_features_monthly is empty; build features first")

    as_of = features["month_start_date"].max()
    if isinstance(as_of, datetime):
        as_of = as_of.date()
    elif hasattr(as_of, "date") and not isinstance(as_of, date):
        as_of = as_of.date()

    run_id = _insert_run(
        engine,
        run_name=run_name or f"material_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        as_of_date=as_of,
        grain="material",
        config=config,
    )

    results: list[dict[str, Any]] = []
    for material_id, group in features.groupby("material_id"):
        try:
            # Additive seasonality is more stable for intermittent SKU demand
            metrics, detail, forecast, cutoff = _train_one_series(
                group,
                grain_id=str(material_id),
                config=config,
                seasonality_mode="additive",
            )
        except Exception as exc:  # noqa: BLE001 - continue other SKUs
            print(f"  skip {material_id}: {exc}")
            continue

        _write_backtest(engine, run_id, str(material_id), metrics, detail)
        n_forecast = _write_forecast(
            engine,
            run_id,
            as_of,
            "material",
            str(material_id),
            forecast,
            cutoff,
            "prophet_with_regressors",
        )
        results.append(
            {
                "material_id": material_id,
                "metrics": metrics,
                "forecast_rows": n_forecast,
            }
        )
        print(
            f"  {material_id}: MAPE={metrics['mape']:.1f}%  "
            f"wMAPE={metrics['wmape']:.1f}%  forecast_rows={n_forecast}"
        )

    return {"run_id": run_id, "grain": "material", "materials": results}


def run_forecast_models(
    engine: Engine | None = None,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    engine = engine or get_forecast_engine()
    print("Training company-level Prophet model...")
    company = run_company_forecast(engine, config)
    print(
        f"  COMPANY: MAPE={company['metrics']['mape']:.1f}%  "
        f"wMAPE={company['metrics']['wmape']:.1f}%"
    )

    print(f"Training material-level Prophet models (top {config.top_materials_limit})...")
    materials = run_material_forecasts(engine, config)
    return {"company": company, "materials": materials}
