-- Bronze-layer migration for transactional tables.
-- Allows duplicate business keys, nullable fields, free-text dates/status,
-- invalid FK references, and non-numeric quantities.

-- purchase_orders
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_material_id_fkey;
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_supplier_id_fkey;
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_quantity_check;
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_status_check;
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_pkey;

ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS bronze_row_id BIGSERIAL;
UPDATE purchase_orders SET bronze_row_id = DEFAULT WHERE bronze_row_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'purchase_orders_bronze_row_id_pkey'
    ) THEN
        ALTER TABLE purchase_orders
            ADD CONSTRAINT purchase_orders_bronze_row_id_pkey PRIMARY KEY (bronze_row_id);
    END IF;
END $$;

ALTER TABLE purchase_orders ALTER COLUMN purchase_order_id DROP NOT NULL;
ALTER TABLE purchase_orders ALTER COLUMN order_date DROP NOT NULL;
ALTER TABLE purchase_orders ALTER COLUMN quantity DROP NOT NULL;

ALTER TABLE purchase_orders
    ALTER COLUMN order_date TYPE TEXT USING order_date::text,
    ALTER COLUMN expected_delivery_date TYPE TEXT USING expected_delivery_date::text,
    ALTER COLUMN quantity TYPE TEXT USING quantity::text,
    ALTER COLUMN status TYPE TEXT,
    ALTER COLUMN supplier_id TYPE TEXT,
    ALTER COLUMN material_id TYPE TEXT,
    ALTER COLUMN purchase_order_id TYPE TEXT;

-- sales_orders
ALTER TABLE sales_orders DROP CONSTRAINT IF EXISTS sales_orders_customer_id_fkey;
ALTER TABLE sales_orders DROP CONSTRAINT IF EXISTS sales_orders_material_id_fkey;
ALTER TABLE sales_orders DROP CONSTRAINT IF EXISTS sales_orders_quantity_check;
ALTER TABLE sales_orders DROP CONSTRAINT IF EXISTS sales_orders_status_check;
ALTER TABLE sales_orders DROP CONSTRAINT IF EXISTS sales_orders_pkey;

ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS bronze_row_id BIGSERIAL;
UPDATE sales_orders SET bronze_row_id = DEFAULT WHERE bronze_row_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'sales_orders_bronze_row_id_pkey'
    ) THEN
        ALTER TABLE sales_orders
            ADD CONSTRAINT sales_orders_bronze_row_id_pkey PRIMARY KEY (bronze_row_id);
    END IF;
END $$;

ALTER TABLE sales_orders ALTER COLUMN sales_order_id DROP NOT NULL;
ALTER TABLE sales_orders ALTER COLUMN order_date DROP NOT NULL;
ALTER TABLE sales_orders ALTER COLUMN quantity DROP NOT NULL;

ALTER TABLE sales_orders
    ALTER COLUMN order_date TYPE TEXT USING order_date::text,
    ALTER COLUMN requested_delivery_date TYPE TEXT USING requested_delivery_date::text,
    ALTER COLUMN quantity TYPE TEXT USING quantity::text,
    ALTER COLUMN status TYPE TEXT,
    ALTER COLUMN customer_id TYPE TEXT,
    ALTER COLUMN material_id TYPE TEXT,
    ALTER COLUMN sales_order_id TYPE TEXT;
