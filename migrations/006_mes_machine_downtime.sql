-- Bronze-layer table for MES machine downtime events.
-- Duplicate business keys, nullable fields, and free-text values are allowed.

CREATE TABLE IF NOT EXISTS machine_downtime (
    bronze_row_id BIGSERIAL PRIMARY KEY,
    downtime_id TEXT,
    plant_id TEXT,
    machine_name TEXT,
    start_time TEXT,
    end_time TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
