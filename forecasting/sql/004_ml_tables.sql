-- Model run metadata, backtest metrics, and forecast outputs

CREATE TABLE IF NOT EXISTS forecast_ml.forecast_runs (
    run_id BIGSERIAL PRIMARY KEY,
    run_name TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    grain TEXT NOT NULL,              -- 'company' | 'material'
    target_column TEXT NOT NULL,
    model_name TEXT NOT NULL,
    horizon_months INTEGER NOT NULL,
    test_months INTEGER NOT NULL,
    top_materials_limit INTEGER,
    params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forecast_ml.forecast_backtest (
    run_id BIGINT NOT NULL REFERENCES forecast_ml.forecast_runs(run_id) ON DELETE CASCADE,
    grain_id TEXT NOT NULL,           -- 'COMPANY' or material_id
    metric_name TEXT NOT NULL,        -- mae | rmse | mape | wmape
    metric_value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (run_id, grain_id, metric_name)
);

CREATE TABLE IF NOT EXISTS forecast_ml.forecast_backtest_detail (
    run_id BIGINT NOT NULL REFERENCES forecast_ml.forecast_runs(run_id) ON DELETE CASCADE,
    grain_id TEXT NOT NULL,
    forecast_month DATE NOT NULL,
    actual DOUBLE PRECISION,
    predicted DOUBLE PRECISION,
    error DOUBLE PRECISION,
    PRIMARY KEY (run_id, grain_id, forecast_month)
);

CREATE TABLE IF NOT EXISTS forecast_ml.sales_forecast_monthly (
    run_id BIGINT NOT NULL REFERENCES forecast_ml.forecast_runs(run_id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    grain TEXT NOT NULL,
    grain_id TEXT NOT NULL,
    forecast_month DATE NOT NULL,
    year_month TEXT NOT NULL,
    yhat DOUBLE PRECISION NOT NULL,
    yhat_lower DOUBLE PRECISION,
    yhat_upper DOUBLE PRECISION,
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, grain_id, forecast_month)
);

CREATE INDEX IF NOT EXISTS idx_sales_forecast_monthly_as_of
    ON forecast_ml.sales_forecast_monthly (as_of_date, grain, grain_id);
