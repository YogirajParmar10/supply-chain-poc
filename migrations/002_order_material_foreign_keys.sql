-- Link order material_id values to materials master data.
-- Invalid or unknown material_id values are set to NULL (keeps missing-value noise).

-- purchase_orders
UPDATE purchase_orders
SET material_id = NULLIF(TRIM(material_id), '')
WHERE material_id IS NOT NULL;

UPDATE purchase_orders AS purchase_order
SET material_id = NULL
WHERE purchase_order.material_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM materials
      WHERE materials.material_id = purchase_order.material_id
        AND materials.material_type = 'RAW_MATERIAL'
  );

ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_material_id_fkey;

ALTER TABLE purchase_orders
    ADD CONSTRAINT purchase_orders_material_id_fkey
    FOREIGN KEY (material_id)
    REFERENCES materials (material_id);

-- sales_orders
UPDATE sales_orders
SET material_id = NULLIF(TRIM(material_id), '')
WHERE material_id IS NOT NULL;

UPDATE sales_orders AS sales_order
SET material_id = NULL
WHERE sales_order.material_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM materials
      WHERE materials.material_id = sales_order.material_id
        AND materials.material_type = 'FINISHED_GOOD'
  );

ALTER TABLE sales_orders DROP CONSTRAINT IF EXISTS sales_orders_material_id_fkey;

ALTER TABLE sales_orders
    ADD CONSTRAINT sales_orders_material_id_fkey
    FOREIGN KEY (material_id)
    REFERENCES materials (material_id);
