# Data Regeneration Log — 5-Year History

**Started:** 2026-07-07  
**Completed:** 2026-07-07  
**Operator:** Cursor agent (user-approved)  
**Goal:** Regenerate clean transactional + WMS data for AI forecasting (5 years)

---

## Request

- Replace existing ~11-month dataset with **5 years** of clean data
- Date window: **2021-07-01 → 2026-07-07** (orders); WMS may extend slightly due to lead times
- Use `--clean` (no bronze noise)
- Truncate transactional tables before regen (`--reset-transactional`)
- Clean `output/wms/` before regen to avoid orphan CSVs

---

## Pre-regeneration state (database)

| Table | Rows | Date range |
|-------|------|------------|
| purchase_orders | 1,367 | 2025-08-02 → 2026-07-06 |
| sales_orders | 2,110 | 2025-08-01 → 2026-07-06 |
| production_orders | 874 | 2025-08-02 → 2026-07-20 |
| production_output | 623 | — |
| inventory_transactions | 3,304 | 2025-08-07 → 2026-07-10 |
| inventory | 22,486 | 338 snapshot days |

## Pre-regeneration state (output/wms)

- inventory CSVs: 338
- inventory_transactions CSVs: 336
- Total size: ~3.2 MB

---

## Steps executed

### 1. Clean local WMS output

```bash
rm -rf output/wms/inventory output/wms/inventory_transactions
mkdir -p output/wms/inventory output/wms/inventory_transactions
```

Removed prior daily CSVs so no orphan files remain after regen.

### 2. Run 5-year history generator

```bash
python scripts/generate_dashboard_history.py \
  --reset-transactional \
  --start-month 2021-07-01 \
  --months 61 \
  --end-date 2026-07-07 \
  --clean
```

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `--reset-transactional` | on | Truncate PO/SO/PR/production_output/inventory tables |
| `--start-month` | 2021-07-01 | First month of 5-year window |
| `--months` | 61 | Jul 2021 through Jul 2026 (partial) |
| `--end-date` | 2026-07-07 | Cap final month |
| `--clean` | on | Disable bronze noise for forecasting-friendly data |

**Runtime:** ~50 seconds

**Full console output:** [`data-regeneration-console.log`](data-regeneration-console.log) (2,121 lines)

### 3. What the script did internally

1. Truncated transactional tables (`purchase_orders`, `sales_orders`, `production_orders`, `production_output`, `inventory`, `inventory_transactions`)
2. Upserted master data (materials, suppliers, customers, plants, warehouses)
3. Generated orders month-by-month for 61 calendar months
4. Generated production output from completed production orders
5. Rebuilt WMS from scratch (day-by-day transactions + full inventory calendar)
6. Exported daily CSVs to `output/wms/`

---

## Post-regeneration state (database)

| Table | Rows | Date range |
|-------|------|------------|
| purchase_orders | 7,110 | 2021-07-01 → 2026-07-07 |
| sales_orders | 10,830 | 2021-07-01 → 2026-07-07 |
| production_orders | 4,537 | 2021-07-02 → 2026-07-20 |
| production_output | 3,204 | — |
| inventory_transactions | 18,813 | 2021-07-05 → 2026-08-06 |
| inventory | 94,896 | 1,859 snapshot days (2021-07-05 → 2026-08-06) |

### Why WMS extends past 2026-07-07

Orders placed on or before 2026-07-07 can have delivery/shipment dates after that day (lead times). The WMS simulator processes those movements, so inventory transactions and snapshots run through **2026-08-06**. This is expected.

---

## Post-regeneration state (output/wms)

| Folder | CSV count | Notes |
|--------|-----------|-------|
| `output/wms/inventory/` | 1,859 | `inventory_2021-07-05.csv` … `inventory_2026-08-06.csv` |
| `output/wms/inventory_transactions/` | 1,855 | One file per transaction day |
| **Total size** | **~15 MB** | Up from ~3.2 MB |

---

## Rollback / recovery

If you need to revert:

- **Database:** No automatic backup was taken. Restore from a Postgres dump if you have one, or re-run with previous parameters (`--start-month 2025-08-01 --months 12`).
- **Output:** Prior WMS CSVs were deleted in step 1; only the new 5-year files exist under `output/wms/`.

---

## Next steps (manual)

1. **Sync to Azure Blob** (upload only new blobs):
   ```bash
   python scripts/sync_to_azure_blob.py \
     --path output/wms/inventory \
     --container databricks \
     --blob-prefix inventory

   python scripts/sync_to_azure_blob.py \
     --path output/wms/inventory_transactions \
     --container databricks \
     --blob-prefix inventory_transactions
   ```
2. **Databricks:** Re-ingest from blob / Postgres source, then re-run silver and gold pipelines.
3. **Validate:** Use `notebooks/validate_gold_tables.ipynb` after gold refresh.

---

## Status

**SUCCESS** — 5-year clean dataset generated and verified.
