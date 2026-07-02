-- Bronze-layer table for MES production orders.
-- Duplicate business keys, nullable fields, and free-text values are allowed.

CREATE TABLE IF NOT EXISTS production_orders (
    bronze_row_id BIGSERIAL PRIMARY KEY,
    production_order_id TEXT,
    plant_id TEXT,
    material_id TEXT,
    planned_quantity TEXT,
    actual_quantity TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
