-- Store end-of-day inventory levels instead of a single point-in-time snapshot.

ALTER TABLE inventory ADD COLUMN IF NOT EXISTS snapshot_date DATE;

UPDATE inventory
SET snapshot_date = CURRENT_DATE
WHERE snapshot_date IS NULL;

ALTER TABLE inventory ALTER COLUMN snapshot_date SET DEFAULT CURRENT_DATE;
