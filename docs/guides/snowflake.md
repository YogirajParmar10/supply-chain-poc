# Snowflake — Context & Loader

Snowflake holds a **replica subset** of the local PostgreSQL generator database for
analytics, SQL exploration, and joins outside the main Databricks Lakeflow pipeline.

**Loader:** `scripts/load_snowflake.py`  
**Dependency:** `snowflake-connector-python[pandas]` (see `requirements.txt`)

---

## Role in the POC

```text
Python generators
       │
       ▼
  PostgreSQL (source of truth)
       │
       ├── Azure Blob ──► Databricks ingest ──► refined ──► serve   (primary pipeline)
       │
       └── load_snowflake.py ──► Snowflake FLEXIPACK.PUBLIC        (parallel SQL store)
```

Databricks ingestion is documented in [`../pipeline/ldp-operations-transformation-pipeline.md`](../pipeline/ldp-operations-transformation-pipeline.md). Snowflake is **not** wired into that LDP notebook flow today; it is a separate destination fed from the same Postgres data.

---

## Snowflake target

| Setting | Env var | Example |
|---------|---------|---------|
| Account | `SF_ACCOUNT` | `mzzcfjf-xk89203` |
| User | `SF_USER` | your Snowflake username |
| Password | `SF_PASSWORD` | your Snowflake password |
| Warehouse | `SF_WAREHOUSE` | `COMPUTE_WH` |
| Database | `SF_DATABASE` | `FLEXIPACK` |
| Schema | `SF_SCHEMA` | `PUBLIC` |

Add these to `.env` (never commit real passwords).

---

## What gets loaded today

`scripts/load_snowflake.py` defines a fixed `LOADS` list:

| Postgres table | Snowflake table | Columns | Strategy |
|----------------|-----------------|---------|----------|
| `plants` | `PLANTS` | all (`*`) | full replace |
| `warehouses` | `WAREHOUSES` | all (`*`) | full replace |
| `production_orders` | `PRODUCTION_ORDERS` | 8 business columns | full replace |
| `production_output` | `PRODUCTION_OUTPUT` | 6 business columns | full replace |

**Not loaded by the script (yet):** `materials`, `suppliers`, `customers`, `purchase_orders`, `sales_orders`, `inventory`, `inventory_transactions`, and other domains.

The module docstring mentions “master, WMS, and MES”; the implementation currently loads **partial master** (plants + warehouses only) and **MES production** tables. WMS tables are not in `LOADS`.

### Approximate Postgres volumes (after 5-year regen, 2026-07-07)

| Table | Rows |
|-------|------|
| `plants` | 2 |
| `warehouses` | 3 |
| `production_orders` | 4,537 |
| `production_output` | 3,204 |
| `materials` | 125 |
| `inventory` | 94,896 |
| `inventory_transactions` | 18,813 |

---

## Load behaviour

1. Read each Postgres table with SQLAlchemy (`SELECT … FROM <table>`).
2. Lowercase all column names in the DataFrame (matches existing Snowflake tables created via CSV upload wizard with quoted lowercase identifiers).
3. Write with `write_pandas(..., overwrite=True, auto_create_table=True, quote_identifiers=True)`.

**Full replace per table** on every run — not incremental upsert. This is intentional: the generator dataset is deterministic and Postgres is the source of truth; Snowflake is a disposable mirror.

Implications:

- Safe to re-run after `generate_dashboard_history.py` or WMS rebuilds.
- Any manual edits in Snowflake are overwritten on the next load.
- Tables not in `LOADS` are untouched by the script (e.g. inventory uploaded manually to Snowflake stays until you extend `LOADS` or delete it).

---

## Usage

```bash
pip install -r requirements.txt

# set SF_* in .env, then:
python -m scripts.load_snowflake
```

Expected output (one line per table):

```text
PLANTS: replaced with 2 rows
WAREHOUSES: replaced with 3 rows
PRODUCTION_ORDERS: replaced with 4537 rows
PRODUCTION_OUTPUT: replaced with 3204 rows
```

---

## Column mapping detail

### `PRODUCTION_ORDERS`

Postgres → Snowflake (same names, lowercased):

- `production_order_id`, `plant_id`, `material_id`
- `planned_quantity`, `actual_quantity`
- `start_date`, `end_date`, `status`

Schema reference: [`schema/mes/production_orders.md`](../../schema/mes/production_orders.md)

### `PRODUCTION_OUTPUT`

- `production_output_id`, `production_order_id`
- `input_material_id`, `input_quantity`
- `output_material_id`, `output_quantity`

Schema reference: [`schema/mes/production_output.md`](../../schema/mes/production_output.md)

Postgres bronze columns such as `bronze_row_id`, `created_at`, and `updated_at` are **excluded** from the production loads (explicit column list).

---

## Comparison with other loaders

| Loader | Target | Strategy | Tables |
|--------|--------|----------|--------|
| `load_snowflake.py` | Snowflake `FLEXIPACK.PUBLIC` | Full replace (`write_pandas` overwrite) | 4 tables |
| `sync_to_azure_blob.py` | Azure Blob | Upload missing blobs only | WMS CSVs |
| `load_servicenow.py` | ServiceNow REST API | Skip existing business keys | MES only |

---

## Extending the loader

To add WMS or full ERP master data:

1. Append a tuple to `LOADS` in `scripts/load_snowflake.py`:

   ```python
   ("inventory", "INVENTORY", "snapshot_date, warehouse_id, material_id, quantity"),
   ```

2. Consider table size — `inventory` has ~95k rows; `write_pandas` overwrite is fine but the upload will take longer than small master tables.

3. Re-run `python -m scripts.load_snowflake`.

For very large tables, consider chunked `write_pandas` or Snowflake `COPY` from staged files instead of a single DataFrame.

---

## Troubleshooting

| Issue | Likely cause |
|-------|----------------|
| `Set SF_ACCOUNT, SF_USER…` | Missing or empty `SF_*` in `.env` |
| Auth / account errors | Wrong account locator, user, or password |
| Column mismatch in Snowflake SQL | Tables created earlier with different casing; loader forces lowercase quoted names |
| Row counts differ from Postgres | Load failed partway; check stderr; only tables in `LOADS` are refreshed |
| Inventory out of sync with production | Inventory not in `LOADS`; reload manually or extend script |

---

## Related files

| Path | Purpose |
|------|---------|
| `scripts/load_snowflake.py` | Postgres → Snowflake loader |
| `generator/utils/db.py` | Postgres connection (loads `.env` on import) |
| `schema/mes/` | MES column definitions |
| `logs/2026-07-07/data-regeneration.md` | Latest full Postgres regen audit |
