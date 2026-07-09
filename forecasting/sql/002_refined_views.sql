-- Cleaned local mirrors of public bronze tables (typed, non-null business keys).
-- These are views so they always reflect the latest public data.

CREATE OR REPLACE VIEW forecast_refined.materials AS
SELECT
    material_id,
    material_name,
    material_type
FROM public.materials
WHERE material_id IS NOT NULL;

CREATE OR REPLACE VIEW forecast_refined.plants AS
SELECT
    plant_id,
    plant_name
FROM public.plants
WHERE plant_id IS NOT NULL;

CREATE OR REPLACE VIEW forecast_refined.sales_orders AS
SELECT
    sales_order_id,
    order_date::date AS order_date,
    customer_id,
    material_id,
    quantity::bigint AS quantity,
    NULLIF(requested_delivery_date, '')::date AS requested_delivery_date,
    UPPER(TRIM(status)) AS status
FROM public.sales_orders
WHERE sales_order_id IS NOT NULL
  AND order_date IS NOT NULL
  AND order_date ~ '^\d{4}-\d{2}-\d{2}'
  AND quantity IS NOT NULL
  AND quantity ~ '^[0-9]+$'
  AND quantity::bigint > 0
  AND material_id IS NOT NULL;

CREATE OR REPLACE VIEW forecast_refined.purchase_orders AS
SELECT
    purchase_order_id,
    order_date::date AS order_date,
    supplier_id,
    material_id,
    quantity::bigint AS quantity,
    NULLIF(expected_delivery_date, '')::date AS expected_delivery_date,
    UPPER(TRIM(status)) AS status
FROM public.purchase_orders
WHERE purchase_order_id IS NOT NULL
  AND order_date IS NOT NULL
  AND order_date ~ '^\d{4}-\d{2}-\d{2}'
  AND quantity IS NOT NULL
  AND quantity ~ '^[0-9]+$'
  AND quantity::bigint > 0
  AND material_id IS NOT NULL;

CREATE OR REPLACE VIEW forecast_refined.production_orders AS
SELECT
    production_order_id,
    plant_id,
    material_id,
    NULLIF(planned_quantity, '')::bigint AS planned_quantity,
    NULLIF(actual_quantity, '')::bigint AS actual_quantity,
    NULLIF(start_date, '')::date AS start_date,
    NULLIF(end_date, '')::date AS end_date,
    UPPER(TRIM(status)) AS status
FROM public.production_orders
WHERE production_order_id IS NOT NULL
  AND material_id IS NOT NULL;

CREATE OR REPLACE VIEW forecast_refined.production_output AS
SELECT
    production_output_id,
    production_order_id,
    input_material_id,
    NULLIF(input_quantity, '')::bigint AS input_quantity,
    output_material_id,
    NULLIF(output_quantity, '')::bigint AS output_quantity
FROM public.production_output
WHERE production_output_id IS NOT NULL
  AND production_order_id IS NOT NULL;

CREATE OR REPLACE VIEW forecast_refined.inventory AS
SELECT
    snapshot_date,
    warehouse_id,
    material_id,
    quantity::bigint AS quantity
FROM public.inventory
WHERE snapshot_date IS NOT NULL
  AND material_id IS NOT NULL
  AND quantity IS NOT NULL
  AND quantity >= 0;

-- machine_downtime may be empty until the forecasting pipeline generates it
CREATE OR REPLACE VIEW forecast_refined.machine_downtime AS
SELECT
    downtime_id,
    plant_id,
    machine_name,
    start_time::timestamp AS start_time,
    end_time::timestamp AS end_time,
    UPPER(TRIM(reason)) AS reason
FROM public.machine_downtime
WHERE downtime_id IS NOT NULL
  AND start_time IS NOT NULL
  AND end_time IS NOT NULL
  AND start_time ~ '^\d{4}-\d{2}-\d{2}'
  AND end_time ~ '^\d{4}-\d{2}-\d{2}';
