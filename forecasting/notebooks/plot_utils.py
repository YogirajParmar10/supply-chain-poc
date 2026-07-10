"""Shared plotting helpers for local forecast notebooks."""

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy.engine import Engine


def latest_run_id(engine: Engine, grain: str) -> int | None:
    df = pd.read_sql(
        f"""
        SELECT run_id
        FROM forecast_ml.forecast_runs
        WHERE grain = '{grain}'
        ORDER BY run_id DESC
        LIMIT 1
        """,
        engine,
    )
    if df.empty:
        return None
    return int(df.iloc[0]["run_id"])


def load_company_history(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT month_start_date, year_month,
               sales_order_count, sales_quantity,
               purchase_quantity, production_output_quantity,
               inventory_on_hand, downtime_hours
        FROM forecast_serve.company_forecast_features_monthly
        ORDER BY month_start_date
        """,
        engine,
        parse_dates=["month_start_date"],
    )


def load_company_forecast(engine: Engine, run_id: int) -> pd.DataFrame:
    return pd.read_sql(
        f"""
        SELECT forecast_month, year_month, yhat, yhat_lower, yhat_upper
        FROM forecast_ml.sales_forecast_monthly
        WHERE run_id = {run_id} AND grain = 'company'
        ORDER BY forecast_month
        """,
        engine,
        parse_dates=["forecast_month"],
    )


def load_backtest_detail(engine: Engine, run_id: int, grain_id: str) -> pd.DataFrame:
    return pd.read_sql(
        f"""
        SELECT forecast_month, actual, predicted, error
        FROM forecast_ml.forecast_backtest_detail
        WHERE run_id = {run_id} AND grain_id = '{grain_id}'
        ORDER BY forecast_month
        """,
        engine,
        parse_dates=["forecast_month"],
    )


def load_backtest_metrics(engine: Engine, run_id: int) -> pd.DataFrame:
    return pd.read_sql(
        f"""
        SELECT grain_id, metric_name, metric_value
        FROM forecast_ml.forecast_backtest
        WHERE run_id = {run_id}
        ORDER BY grain_id, metric_name
        """,
        engine,
    )


def load_material_history(engine: Engine, material_id: str) -> pd.DataFrame:
    return pd.read_sql(
        f"""
        SELECT month_start_date, year_month, sales_quantity,
               purchase_quantity, production_output_quantity,
               inventory_on_hand, downtime_hours
        FROM forecast_serve.forecast_features_monthly
        WHERE material_id = '{material_id}'
        ORDER BY month_start_date
        """,
        engine,
        parse_dates=["month_start_date"],
    )


def load_material_forecast(engine: Engine, run_id: int, material_id: str) -> pd.DataFrame:
    return pd.read_sql(
        f"""
        SELECT forecast_month, year_month, yhat, yhat_lower, yhat_upper
        FROM forecast_ml.sales_forecast_monthly
        WHERE run_id = {run_id}
          AND grain = 'material'
          AND grain_id = '{material_id}'
        ORDER BY forecast_month
        """,
        engine,
        parse_dates=["forecast_month"],
    )


def load_top_materials(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT sales_rank, material_id, material_name, sold_quantity
        FROM forecast_serve.top_selling_materials
        ORDER BY sales_rank
        """,
        engine,
    )


def style_axes(ax: plt.Axes, *, ylabel: str, title: str) -> None:
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def plot_history_and_forecast(
    history: pd.DataFrame,
    forecast: pd.DataFrame,
    *,
    date_col: str,
    value_col: str,
    title: str,
    ylabel: str,
    figsize: tuple[float, float] = (14, 6),
) -> plt.Figure:
    cutoff = history[date_col].max()
    hist = history[[date_col, value_col]].rename(columns={date_col: "ds", value_col: "y"})
    fc = forecast.rename(columns={"forecast_month": "ds"})

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(hist["ds"], hist["y"], label="Historical", color="steelblue", marker="o", ms=4, linewidth=1.5)
    ax.plot(fc["ds"], fc["yhat"], label="Forecast", color="tomato", linewidth=2)
    ax.fill_between(
        fc["ds"],
        fc["yhat_lower"],
        fc["yhat_upper"],
        alpha=0.2,
        color="tomato",
        label="95% Confidence Interval",
    )
    ax.axvline(cutoff, linestyle="--", color="gray", linewidth=1.2, label="Forecast Start")
    style_axes(ax, ylabel=ylabel, title=title)
    ax.set_xlabel("Month")
    ax.legend()
    fig.autofmt_xdate(rotation=30)
    plt.tight_layout()
    return fig


def plot_backtest(actuals: pd.DataFrame, *, title: str, ylabel: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(
        actuals["forecast_month"],
        actuals["actual"],
        marker="o",
        label="Actual",
        color="steelblue",
        linewidth=1.8,
    )
    ax.plot(
        actuals["forecast_month"],
        actuals["predicted"],
        marker="s",
        label="Predicted (holdout)",
        color="tomato",
        linewidth=1.8,
    )
    style_axes(ax, ylabel=ylabel, title=title)
    ax.set_xlabel("Month")
    ax.legend()
    fig.autofmt_xdate(rotation=30)
    plt.tight_layout()
    return fig
