# Lakeflow Declarative Pipeline: Operations Transformation

Transforms ingested supply-chain data into cleaned **refined** (silver) tables and analytical **serve** (gold) tables for FlexiPack Industries Ltd.

The transformation is split into **two importable notebooks** and **two pipelines**, designed to run as separate stages in a Databricks Workflow.

| Stage | Pipeline | Notebook | Target schema |
|-------|----------|----------|---------------|
| Silver | `operations_silver_transformation_pipeline` | `notebooks/ldp_silver_transformations.ipynb` | `refined` |
| Gold | `operations_gold_transformation_pipeline` | `notebooks/ldp_gold_transformations.ipynb` | `serve` |

| Item | Value |
|------|-------|
| Catalog | `jm_databricks_learning_ws` |
| Source schema | `ingest` |

## Architecture

```text
ingest (bronze — streaming tables)              ingest (bronze — Delta via Fivetran)
├── customers, materials, ...                   ├── inventory
├── purchase_orders, sales_orders               └── inventory_transactions
        │                                               │
        └───────────────────┬───────────────────────────┘
                            ▼
           operations_silver_transformation_pipeline
              (ldp_silver_transformations.ipynb)
                   batch read → materialized views
                            │
                            ▼
                    refined (9 materialized views)
                            │
                            ▼
            operations_gold_transformation_pipeline
               (ldp_gold_transformations.ipynb)
                            │
                            ▼
                    serve (4 materialized views)
```

**Architecture:** Bronze (streaming) → Silver (materialized views) → Gold (materialized views)

Silver reads bronze with `spark.read.table(...)` (batch snapshot) so window-based deduplication (`row_number()`) is supported. Table names in `refined` are unchanged; the gold pipeline requires no modifications.

## Import notebooks into Databricks

1. In the workspace, go to **Workspace** → your target folder (e.g. `supply-chain-poc/notebooks`).
2. Click **⋮** → **Import**.
3. Select **File** and upload:
   - `ldp_silver_transformations.ipynb`
   - `ldp_gold_transformations.ipynb`
4. Choose **Import as**: **Notebook** (default).

Alternatively, if the repo is connected via **Databricks Repos**, the `.ipynb` files are available directly at `notebooks/ldp_silver_transformations` and `notebooks/ldp_gold_transformations`.

---

## Prerequisites

1. **Unity Catalog** schemas exist (or will be auto-created on first run):
   - `jm_databricks_learning_ws.ingest` — populated by ingestion (out of scope)
   - `jm_databricks_learning_ws.refined`
   - `jm_databricks_learning_ws.serve`

2. **Source tables** are available:

   | Source | Type | Tables |
   |--------|------|--------|
   | Lakeflow Connect | Streaming table | `customers`, `materials`, `plants`, `suppliers`, `warehouses`, `purchase_orders`, `sales_orders` |
   | Fivetran | Delta (batch) | `inventory`, `inventory_transactions` |

3. **Permissions** on the pipeline run identity:
   - `USE CATALOG`, `USE SCHEMA`, `CREATE TABLE` on `refined` and `serve`
   - `SELECT` on all `ingest` source tables

---

## Create the pipelines

### Silver pipeline

1. **Jobs & Pipelines** → **Create** → **ETL Pipeline**.
2. **Pipeline name**: `operations_silver_transformation_pipeline`
3. **Default location for data assets**:
   - Catalog: `jm_databricks_learning_ws`
   - Schema: `refined`
4. Add `ldp_silver_transformations` as the sole source notebook.
5. Enable **Serverless** + **Photon**, channel **Current**.
6. Save and run.

### Gold pipeline

1. **Jobs & Pipelines** → **Create** → **ETL Pipeline**.
2. **Pipeline name**: `operations_gold_transformation_pipeline`
3. **Default location for data assets**:
   - Catalog: `jm_databricks_learning_ws`
   - Schema: `serve`
4. Add `ldp_gold_transformations` as the sole source notebook.
5. Enable **Serverless** + **Photon**, channel **Current**.
6. Save (do not run until silver has completed at least once).

### CLI / REST API

Update notebook paths in the JSON templates, then:

```bash
databricks pipelines create --json @databricks/pipelines/operations_silver_transformation_pipeline.json
databricks pipelines create --json @databricks/pipelines/operations_gold_transformation_pipeline.json
```

---

## Databricks Workflow (recommended)

Chain silver and gold as separate tasks so each stage can be monitored, retried, and scheduled independently.

1. **Jobs & Pipelines** → **Create** → **Job**.
2. **Task 1 — Silver**
   - Type: **Lakeflow Declarative Pipeline** (ETL Pipeline)
   - Pipeline: `operations_silver_transformation_pipeline`
3. **Task 2 — Gold**
   - Type: **Lakeflow Declarative Pipeline**
   - Pipeline: `operations_gold_transformation_pipeline`
   - **Depends on**: Task 1 (silver)
4. Save and run the job.

```text
master_ingestion_pipeline
├── silver_transformation        (operations_silver_transformation_pipeline)
├── gold_transformation          (operations_gold_transformation_pipeline)
└── validate_gold_tables         (notebook task — depends on gold)
```

---

## Gold validation notebook

Import and wire `notebooks/validate_gold_tables.ipynb` as the final task in the master ingestion workflow.

The notebook:

- Discovers tables in `jm_databricks_learning_ws.serve`
- Validates existence, row counts, key uniqueness, required columns, and freshness (when a timestamp column exists)
- Prints a PASS/FAIL summary and calls `dbutils.notebook.exit("SUCCESS")` on success
- Raises an exception on failure so the job stops immediately

To add a new gold table later, append an entry to `GOLD_TABLE_RULES` in the notebook configuration cell.

---

## Configuration reference

| Setting | Silver | Gold |
|---------|--------|------|
| Pipeline name | `operations_silver_transformation_pipeline` | `operations_gold_transformation_pipeline` |
| Notebook | `ldp_silver_transformations.ipynb` | `ldp_gold_transformations.ipynb` |
| Default schema | `refined` | `serve` |
| Continuous mode | `false` | `false` |
| Photon | `true` | `true` |
| Checkpoints | Managed by pipeline | Managed by pipeline |
| `writeStream()` | Not used | Not used |

---

## Data quality rules (silver / `refined`)

Rules are implemented in `ldp_silver_transformations.ipynb`.

### ERP master tables (streaming)

| Rule | Implementation |
|------|----------------|
| Remove null primary keys | Filter blank / null business keys |
| Trim strings | `trim()` on all text columns |
| Dedupe business keys | Window dedupe using available metadata (`updated_at`, etc.); `bronze_row_id` is **not** used on master tables |
| Normalize enums | `material_type` uppercased |

### ERP order tables

| Rule | Implementation |
|------|----------------|
| Dedupe business keys | Latest `bronze_row_id` per `purchase_order_id` / `sales_order_id` when present |
| Trim strings | All identifier and date text columns |
| Normalize status | Map common variants to canonical values; uppercase |
| Filter invalid quantities | Parse text qty; drop ≤ 0 or non-numeric |
| Parse dates | ISO, datetime, EU, and text-month formats |
| Expectations | `@dp.expect_or_drop` on keys and positive quantity |

### WMS tables (batch)

| Rule | Implementation |
|------|----------------|
| Remove null identifiers | Required keys must be non-null and non-blank |
| Trim strings | All text columns |
| Filter invalid quantities | Positive integers only |
| Dedupe | By `transaction_id` or `(snapshot_date, warehouse_id, material_id)` using `_fivetran_synced` / `updated_at` when present |

---

## Tables produced

### Silver — `jm_databricks_learning_ws.refined`

| Table | Source | Type | Description |
|-------|--------|------|-------------|
| `customers` | `ingest.customers` | Materialized view | Clean customer master; deduped on `customer_id` |
| `materials` | `ingest.materials` | Materialized view | Clean material master; `material_type` normalized |
| `plants` | `ingest.plants` | Materialized view | Clean plant master |
| `suppliers` | `ingest.suppliers` | Materialized view | Clean supplier master |
| `warehouses` | `ingest.warehouses` | Materialized view | Clean warehouse master |
| `purchase_orders` | `ingest.purchase_orders` | Materialized view | Deduped POs; trimmed, typed qty/dates, normalized status |
| `sales_orders` | `ingest.sales_orders` | Materialized view | Deduped SOs; trimmed, typed qty/dates, normalized status |
| `inventory` | `ingest.inventory` | Materialized view | Daily inventory snapshots; positive qty only |
| `inventory_transactions` | `ingest.inventory_transactions` | Materialized view | Clean movement ledger; deduped on `transaction_id` |

### Gold — `jm_databricks_learning_ws.serve`

| Table | Grain | Metrics | Sources |
|-------|-------|---------|---------|
| `supplier_summary` | `supplier_id` | `total_purchase_orders`, `total_quantity` | `refined.purchase_orders` + `refined.suppliers` |
| `customer_summary` | `customer_id` | `total_sales_orders`, `total_quantity` | `refined.sales_orders` + `refined.customers` |
| `inventory_summary` | `warehouse_id` | `current_stock`, `total_materials` | Latest `refined.inventory` snapshot + `refined.warehouses` |
| `material_summary` | `material_id` | `purchased_quantity`, `sold_quantity`, `current_inventory` | `refined.purchase_orders`, `refined.sales_orders`, latest `refined.inventory`, `refined.materials` |

---

## Validation steps

Run after each stage completes.

### After silver

```sql
-- No duplicate business keys in refined orders
SELECT purchase_order_id, COUNT(*) AS cnt
FROM jm_databricks_learning_ws.refined.purchase_orders
GROUP BY purchase_order_id
HAVING COUNT(*) > 1;

SELECT COUNT(*) FROM jm_databricks_learning_ws.refined.purchase_orders
WHERE quantity IS NULL OR quantity <= 0;
-- Expect 0
```

### After gold

```sql
-- Supplier totals should match refined purchase orders
SELECT
  (SELECT SUM(total_quantity) FROM jm_databricks_learning_ws.serve.supplier_summary) AS gold_qty,
  (SELECT SUM(quantity) FROM jm_databricks_learning_ws.refined.purchase_orders) AS refined_qty;

-- Material purchased quantity should match refined POs
SELECT
  (SELECT SUM(purchased_quantity) FROM jm_databricks_learning_ws.serve.material_summary) AS gold_purchased,
  (SELECT SUM(quantity) FROM jm_databricks_learning_ws.refined.purchase_orders) AS refined_purchased;
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Gold pipeline fails | Silver not run yet | Run silver pipeline first |
| Table not found in `ingest` | Ingestion not configured | Verify Lakeflow Connect / Fivetran |
| Permission denied on `serve` | Missing CREATE TABLE | Grant UC privileges on `serve` |
| Mass expectation drops | Column name mismatch | Compare ingest schema to notebook |
| Streaming table empty | Connect not running | Start Lakeflow Connect ingestion |

---

## Related files

| File | Purpose |
|------|---------|
| `notebooks/ldp_silver_transformations.ipynb` | Silver pipeline notebook (importable) |
| `notebooks/ldp_gold_transformations.ipynb` | Gold pipeline notebook (importable) |
| `databricks/pipelines/operations_silver_transformation_pipeline.json` | Silver pipeline API template |
| `databricks/pipelines/operations_gold_transformation_pipeline.json` | Gold pipeline API template |
| `notebooks/validate_gold_tables.ipynb` | Post-pipeline gold table validation job task |
