-- Databricks Unity Catalog ML schema tables (Delta)
-- Run once in a SQL warehouse or the training notebook setup cell.

CREATE SCHEMA IF NOT EXISTS jm_databricks_learning_ws.ml;

CREATE TABLE IF NOT EXISTS jm_databricks_learning_ws.ml.forecast_runs (
    run_id BIGINT,
    run_name STRING,
    as_of_date DATE,
    grain STRING,
    target_column STRING,
    model_name STRING,
    horizon_months INT,
    test_months INT,
    top_materials_limit INT,
    params_json STRING,
    created_at TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS jm_databricks_learning_ws.ml.forecast_backtest (
    run_id BIGINT,
    grain_id STRING,
    metric_name STRING,
    metric_value DOUBLE
) USING DELTA;

CREATE TABLE IF NOT EXISTS jm_databricks_learning_ws.ml.forecast_backtest_detail (
    run_id BIGINT,
    grain_id STRING,
    forecast_month DATE,
    actual DOUBLE,
    predicted DOUBLE,
    error DOUBLE
) USING DELTA;

CREATE TABLE IF NOT EXISTS jm_databricks_learning_ws.ml.sales_forecast_monthly (
    run_id BIGINT,
    as_of_date DATE,
    grain STRING,
    grain_id STRING,
    forecast_month DATE,
    year_month STRING,
    yhat DOUBLE,
    yhat_lower DOUBLE,
    yhat_upper DOUBLE,
    model_name STRING,
    created_at TIMESTAMP
) USING DELTA;
