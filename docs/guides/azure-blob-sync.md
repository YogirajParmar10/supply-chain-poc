# Azure Blob File Sync

Sync generated files to Azure Blob Storage **without running generators** and without duplicate uploads.

## 1) Install dependency

```bash
pip install -r requirements.txt
```

This includes `azure-storage-blob`.

## 2) Configure credentials

Set Azure Storage connection string in environment or `.env`:

```bash
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
```

## 3) Run sync command

Use `scripts/sync_to_azure_blob.py` and provide:

- target `--container`
- optional `--blob-prefix`
- at least one of `--file`, `--path`, or `--glob`

### Examples

Sync one file (uploads to `inventory/inventory_2026-07-06.csv` in the container):

```bash
python scripts/sync_to_azure_blob.py \
  --file output/wms/inventory/inventory_2026-07-06.csv \
  --container databricks \
  --blob-prefix inventory
```

Sync all WMS inventory CSVs recursively (flat under prefix):

```bash
python scripts/sync_to_azure_blob.py \
  --path output/wms/inventory \
  --container databricks \
  --blob-prefix inventory
```

Sync by glob from repository root:

```bash
python scripts/sync_to_azure_blob.py \
  --glob "output/wms/**/*.csv" \
  --container scpoc \
  --blob-prefix raw \
  --source-root .
```

Preview only (no upload):

```bash
python scripts/sync_to_azure_blob.py \
  --glob "output/wms/**/*.csv" \
  --container scpoc \
  --blob-prefix raw \
  --dry-run
```

## 4) How blob paths are built

By default, each file is uploaded as:

`<blob-prefix>/<filename>`

Example:

- local: `output/wms/inventory/inventory_2026-07-11.csv`
- container: `databricks`
- blob prefix: `inventory`
- result: `databricks/inventory/inventory_2026-07-11.csv`

To keep local folder structure under the prefix, pass `--preserve-paths` and set
`--source-root` (for example `--source-root output/wms`).

## 5) How duplicate prevention works

For each local file, the script computes the blob path above.

Before upload it checks whether that blob already exists:

- exists -> **skip**
- missing -> **upload**

So rerunning the same sync command is idempotent and does not duplicate files in Blob Storage.

## 6) Output summary

The script prints:

- `uploaded`
- `skipped_existing`
- `failed`

Use this summary to confirm what changed in each sync run.

## 7) Run logs

Save operational audit logs under `logs/YYYY-MM-DD/` (summary `.md` + console `.log`). See [`logs/README.md`](../../logs/README.md).
