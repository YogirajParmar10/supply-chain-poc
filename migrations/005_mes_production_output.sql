-- Bronze-layer table for MES production output.
-- Duplicate business keys, nullable fields, and free-text values are allowed.

CREATE TABLE IF NOT EXISTS production_output (
    bronze_row_id BIGSERIAL PRIMARY KEY,
    production_output_id TEXT,
    production_order_id TEXT,
    input_material_id TEXT,
    input_quantity TEXT,
    output_material_id TEXT,
    output_quantity TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
