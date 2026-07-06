-- Add active flag to customer and supplier master data for dashboard partner KPIs.

ALTER TABLE customers ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;
