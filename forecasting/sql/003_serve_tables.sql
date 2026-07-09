-- Gold / serve feature tables used by the forecasting models

CREATE TABLE IF NOT EXISTS forecast_serve.sales_trend_monthly (
    month_start_date DATE NOT NULL PRIMARY KEY,
    year_month TEXT NOT NULL,
    order_count BIGINT NOT NULL,
    total_quantity BIGINT NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forecast_serve.top_selling_materials (
    sales_rank INTEGER NOT NULL,
    material_id TEXT NOT NULL PRIMARY KEY,
    material_name TEXT,
    material_type TEXT,
    sold_quantity BIGINT NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forecast_serve.material_summary (
    material_id TEXT NOT NULL PRIMARY KEY,
    material_name TEXT,
    material_type TEXT,
    purchased_quantity BIGINT NOT NULL,
    sold_quantity BIGINT NOT NULL,
    current_inventory BIGINT NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forecast_serve.material_procurement_trend_monthly (
    material_id TEXT NOT NULL,
    material_name TEXT,
    material_type TEXT,
    month_start_date DATE NOT NULL,
    year_month TEXT NOT NULL,
    purchase_order_count BIGINT NOT NULL,
    purchase_quantity BIGINT NOT NULL,
    sales_order_count BIGINT NOT NULL,
    sales_quantity BIGINT NOT NULL,
    production_input_quantity BIGINT NOT NULL,
    production_output_quantity BIGINT NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (material_id, month_start_date)
);

CREATE TABLE IF NOT EXISTS forecast_serve.inventory_monthly (
    material_id TEXT NOT NULL,
    month_start_date DATE NOT NULL,
    year_month TEXT NOT NULL,
    inventory_on_hand BIGINT NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (material_id, month_start_date)
);

CREATE TABLE IF NOT EXISTS forecast_serve.machine_downtime_monthly (
    plant_id TEXT NOT NULL,
    month_start_date DATE NOT NULL,
    year_month TEXT NOT NULL,
    downtime_event_count BIGINT NOT NULL,
    downtime_hours DOUBLE PRECISION NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (plant_id, month_start_date)
);

-- Model-ready feature matrix (top finished goods + exogenous signals)
CREATE TABLE IF NOT EXISTS forecast_serve.forecast_features_monthly (
    material_id TEXT NOT NULL,
    material_name TEXT,
    month_start_date DATE NOT NULL,
    year_month TEXT NOT NULL,
    sales_order_count BIGINT NOT NULL,
    sales_quantity BIGINT NOT NULL,
    purchase_order_count BIGINT NOT NULL,
    purchase_quantity BIGINT NOT NULL,
    production_input_quantity BIGINT NOT NULL,
    production_output_quantity BIGINT NOT NULL,
    inventory_on_hand BIGINT NOT NULL,
    downtime_hours DOUBLE PRECISION NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (material_id, month_start_date)
);

CREATE TABLE IF NOT EXISTS forecast_serve.company_forecast_features_monthly (
    month_start_date DATE NOT NULL PRIMARY KEY,
    year_month TEXT NOT NULL,
    sales_order_count BIGINT NOT NULL,
    sales_quantity BIGINT NOT NULL,
    purchase_quantity BIGINT NOT NULL,
    production_output_quantity BIGINT NOT NULL,
    inventory_on_hand BIGINT NOT NULL,
    downtime_hours DOUBLE PRECISION NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
