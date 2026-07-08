# Snowflake Migration Log

**Started:** 2026-07-08  
**Completed:** 2026-07-08  
**Operator:** Cursor agent (user-approved)  
**Goal:** Replace all rows in Snowflake `FLEXIPACK.PUBLIC` tables from local Postgres (5-year dataset)

---

## Target tables (Snowflake)

User confirmed 4 tables in `FLEXIPACK.PUBLIC`:

- `PLANTS`
- `WAREHOUSES`
- `PRODUCTION_ORDERS`
- `PRODUCTION_OUTPUT`

## Approach

Used `scripts/load_snowflake.py` with `write_pandas(..., overwrite=True)`.

This **replaces each table in one step** (equivalent to truncate + reload). No manual `DROP TABLE` or `DELETE` was required.

---

## Postgres source (pre-migration)

| Postgres table | Rows |
|----------------|------|
| `plants` | 2 |
| `warehouses` | 3 |
| `production_orders` | 4,537 |
| `production_output` | 3,204 |

---

## Steps executed

### 1. Install Snowflake connector (first run failed — module missing)

```bash
pip install 'snowflake-connector-python[pandas]>=3.12.0'
```

### 2. Run loader

```bash
python -m scripts.load_snowflake
```

**Loader output:**

```text
PLANTS: replaced with 2 rows
WAREHOUSES: replaced with 3 rows
PRODUCTION_ORDERS: replaced with 4537 rows
PRODUCTION_OUTPUT: replaced with 3204 rows
```

**Runtime:** ~34 seconds

### 3. Post-migration verification (Snowflake `SELECT COUNT(*)`)

| Snowflake table | Rows | Matches Postgres |
|-----------------|------|------------------|
| `PLANTS` | 2 | yes |
| `WAREHOUSES` | 3 | yes |
| `PRODUCTION_ORDERS` | 4,537 | yes |
| `PRODUCTION_OUTPUT` | 3,204 | yes |

---

## Console log

Full output: [`snowflake-migration-console.log`](snowflake-migration-console.log)

---

## Recovery

Re-run the same command after any Postgres regen:

```bash
python -m scripts.load_snowflake
```

Each table is fully overwritten; no incremental state on the Snowflake side.

---

## Status

**SUCCESS** — All 4 tables replaced; row counts match Postgres.
