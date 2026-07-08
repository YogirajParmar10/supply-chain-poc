# Azure Blob WMS Sync Log

**Started:** 2026-07-07  
**Completed:** 2026-07-07  
**Operator:** Cursor agent (user-approved)  
**Goal:** Full upload of regenerated 5-year WMS CSVs after user deleted old blobs

---

## Context

- User deleted existing blobs under:
  - `databricks/inventory/*`
  - `databricks/inventory_transactions/*`
- Local source: `output/wms/` from 5-year regeneration (see [`data-regeneration.md`](data-regeneration.md))
- Sync mode: upload missing blobs only (skip if blob already exists)

---

## Pre-sync local state

| Folder | File count | Size |
|--------|------------|------|
| `output/wms/inventory/` | 1,859 | ~7.3 MB |
| `output/wms/inventory_transactions/` | 1,855 | ~7.3 MB |
| **Total** | **3,714** | **~15 MB** |

**Local date coverage:**

- Inventory: `inventory_2021-07-05.csv` → `inventory_2026-08-06.csv`
- Transactions: `inventory_transactions_2021-07-05.csv` → `inventory_transactions_2026-08-06.csv`

---

## Azure target paths

| Local folder | Container | Blob prefix | Example blob path |
|--------------|-----------|-------------|-------------------|
| `output/wms/inventory/` | `databricks` | `inventory` | `databricks/inventory/inventory_2021-07-05.csv` |
| `output/wms/inventory_transactions/` | `databricks` | `inventory_transactions` | `databricks/inventory_transactions/inventory_transactions_2021-07-05.csv` |

---

## Commands executed

### Dry-run (path validation)

```bash
python scripts/sync_to_azure_blob.py \
  --path output/wms/inventory \
  --container databricks \
  --blob-prefix inventory \
  --dry-run
```

Confirmed flat path mapping: `inventory/<filename>.csv`

### Inventory upload

```bash
python scripts/sync_to_azure_blob.py \
  --path output/wms/inventory \
  --container databricks \
  --blob-prefix inventory
```

### Inventory transactions upload

```bash
python scripts/sync_to_azure_blob.py \
  --path output/wms/inventory_transactions \
  --container databricks \
  --blob-prefix inventory_transactions
```

---

## Run timeline

| Phase | Time (UTC) | Notes |
|-------|------------|-------|
| Initial inventory upload | 13:00–13:05 | Interrupted after ~750 files (session timeout) |
| Resume + complete | 13:07–13:39 | Skipped 977 existing inventory blobs; uploaded remainder + all transactions |

**Total runtime (resume session):** ~32 minutes

---

## Results

### Inventory (`databricks/inventory/`)

| Metric | Count |
|--------|-------|
| Uploaded (initial run) | ~750 |
| Uploaded (resume run) | 882 |
| Skipped (already in blob) | 977 |
| Failed | 0 |
| **Total blobs** | **1,859** |

### Inventory transactions (`databricks/inventory_transactions/`)

| Metric | Count |
|--------|-------|
| Uploaded | 1,855 |
| Skipped | 0 |
| Failed | 0 |
| **Total blobs** | **1,855** |

### Grand total

| Metric | Count |
|--------|-------|
| Files synced to Azure | **3,714** |
| Failures | **0** |

---

## Log files

| File | Description |
|------|-------------|
| [`azure-blob-sync-console.log`](azure-blob-sync-console.log) | Full per-file upload/skip log (4,481 lines) |
| This file | Summary and audit trail |

---

## Recovery notes

- **Interrupted sync:** Re-run the same command; existing blobs are skipped automatically.
- **Partial Azure state:** Delete the prefix in Azure Portal, then re-run full sync.
- **Databricks mismatch:** After blob refresh, truncate/re-ingest bronze WMS tables and re-run silver + gold pipelines.

---

## Next steps (manual)

1. In Databricks, re-ingest from `databricks/inventory/*` and `databricks/inventory_transactions/*`
2. Re-run `ldp_silver_transformations` and `ldp_gold_transformations`
3. Validate with `notebooks/validate_gold_tables.ipynb`
4. Also refresh ERP transactional sources (PO/SO/PR) if not already updated in Databricks

---

## Status

**SUCCESS** — All 3,714 WMS CSV files uploaded to Azure Blob Storage with 0 failures.
