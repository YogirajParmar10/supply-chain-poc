# ServiceNow Setup Guide — MES Data Source for Databricks Ingestion

This document records the full setup of a free ServiceNow instance as a source
system for the supply-chain POC, holding MES data (`production_orders`,
`production_output`) that is ingested into Databricks via the Lakeflow Connect
ServiceNow connector.

**Result of this setup:**

| Item | Value |
|---|---|
| Instance | `https://dev404273.service-now.com` (Personal Developer Instance, Australia release) |
| Custom tables | `u_production_order` (8 columns), `u_production_output` (6 columns) |
| OAuth app | `databricks` (System OAuth → Application Registry) |
| Data loader | `scripts/load_servicenow.py` (Postgres → ServiceNow REST Table API) |

---

## 1. Create a free ServiceNow Personal Developer Instance (PDI)

1. Go to **https://developer.servicenow.com** and click **Sign In** (create a
   ServiceNow ID if you don't have one).
2. Complete the first-time onboarding questions (answers don't restrict anything).
3. Click **Request Instance** (top right, or avatar → **My Instance**).
4. Choose the **latest release** (tagged "Latest release") and click **Request**.
   High demand can queue the request for a while.
5. When assigned, the **Manage my instance** page shows:
   - **Instance URL** — e.g. `https://dev404273.service-now.com`
   - **User name** — `admin`
   - **Current password** — reveal with the eye icon; copy it
6. Click the Instance URL and log in as `admin`.

> **PDI lifecycle rules (official PDI Guide):**
> - The instance **hibernates** after a few hours of inactivity. Data is
>   preserved; wake it by logging into the developer portal.
> - After **10 days without developer-portal activity the instance is
>   reclaimed** (wiped and reassigned). Log in at least weekly.
> - The instance login (`admin` + instance password) is **different** from the
>   developer-portal account login.

---

## 2. Create the custom tables

UI path (repeat for each table):

1. **All → System Definition → Tables → New**
2. **Label:** `Production Order` — the internal name auto-fills as
   `u_production_order`. Leave "Extends table" empty.
3. In the **Columns** tab, click *Insert a new row...* and add each column.
4. **Submit**.

### Table 1 — `u_production_order`

| Column label | Column name | Type | Notes |
|---|---|---|---|
| Production Order ID | `u_production_order_id` | String (40) | Unique = true (business key) |
| Plant ID | `u_plant_id` | String (40) | |
| Material ID | `u_material_id` | String (40) | |
| Planned Quantity | `u_planned_quantity` | Decimal | |
| Actual Quantity | `u_actual_quantity` | Decimal | |
| Start Date | `u_start_date` | Date | |
| End Date | `u_end_date` | Date | |
| Status | `u_status` | String (40) | String, not Choice — source data intentionally contains dirty values (`COMPLETE`, `RUNNING`, blanks) |

### Table 2 — `u_production_output`

| Column label | Column name | Type | Notes |
|---|---|---|---|
| Production Output ID | `u_production_output_id` | String (40) | Unique = true (business key) |
| Production Order ID | `u_production_order_id` | String (40) | |
| Input Material ID | `u_input_material_id` | String (40) | |
| Input Quantity | `u_input_quantity` | Decimal | |
| Output Material ID | `u_output_material_id` | String (40) | |
| Output Quantity | `u_output_quantity` | Decimal | |

> Every table automatically gets `sys_id`, `sys_created_on`, `sys_updated_on`
> and other system columns. The Databricks connector uses `sys_updated_on` as
> its incremental-sync cursor.

> **API alternative (what we actually used):** tables can also be created over
> REST by POSTing the table to `/api/now/table/sys_db_object` and each column
> to `/api/now/table/sys_dictionary` (fields: `name`, `element`,
> `column_label`, `internal_type` = `string` / `decimal` / `glide_date`,
> `max_length`, `unique`).

---

## 3. Create the OAuth app (credentials for Databricks)

1. **All → System OAuth → Application Registry → New**
2. Choose **"Create an OAuth API endpoint for external clients"**.
3. Fill in:

| Field | Value |
|---|---|
| Name | `databricks` |
| Client Secret | leave blank (auto-generated) |
| Redirect URL | `https://<databricks-workspace-host>/login/oauth/servicenow.html` (e.g. `https://adb-7405617060023106.6.azuredatabricks.net/login/oauth/servicenow.html` — exact match required, no trailing slash) |
| Auth Scopes (related list) | `useraccount` |
| everything else | defaults (Active ✓, Refresh Token 8,640,000 s, Access Token 1,800 s) |

4. **Submit**, then reopen the `databricks` record and copy:
   - **Client ID**
   - **Client Secret** (click the padlock/eye icon to reveal)

---

## 4. Create the connection in Databricks

1. In the Databricks workspace: **+ New → Add or upload data → ServiceNow**.
2. In *Create a connection to ServiceNow*:

| Field | Value |
|---|---|
| Auth Type | OAuth (recommended) |
| Connection name | `servicenow_flexipack` |
| Instance URL | `https://dev404273.service-now.com` |
| Client ID / Client secret | from step 3 |

3. Click **Authenticate and create connection**. In the popup, log in as
   **`admin` with the instance password** (not the developer-portal account)
   and click **Allow**.

> Troubleshooting:
> - *"User name or password invalid"* — you are using the developer-portal
>   credentials, or the instance password is stale. Reset it from the
>   developer portal (Manage my instance) and retry.
> - *redirect_uri mismatch* — the Redirect URL in the OAuth app doesn't
>   exactly match the workspace URL.
> - Popup never loads — the PDI is hibernating; wake it first.

---

## 5. Load MES data into the ServiceNow tables

Prerequisites in `.env` (project root):

```
DATABASE_URL=postgresql://...          # existing
SN_INSTANCE=https://dev404273.service-now.com
SN_USER=admin
SN_PASSWORD=<instance admin password>
```

Run (requires Python 3.12+; the venv must not be the macOS system 3.9):

```bash
python -m scripts.load_servicenow --limit 10   # smoke test: 10 rows per table
python -m scripts.load_servicenow              # full load (1,010 + 704 rows)
```

The script reads from Postgres and POSTs to
`/api/now/table/u_production_order` / `u_production_output`. It is
**idempotent** — records whose business key already exists in ServiceNow are
skipped, so it can be re-run safely.

Verify in the UI: open
`https://dev404273.service-now.com/u_production_order_list.do` and
`.../u_production_output_list.do`, or type `u_production_order.list` in the
**All** filter box and press Enter (the menu will say "No Results" — press
Enter anyway).

---

## 6. Ingest into Databricks

1. Reopen the ingestion wizard (**+ New → Add or upload data → ServiceNow**,
   reusing the `servicenow_flexipack` connection).
2. **Source:** select `u_production_order` and `u_production_output`.
3. **Destination:** target catalog + schema (bronze layer).
4. **Schedule:** manual for the POC (scheduled runs fail while the PDI
   hibernates — wake the instance before each run).
5. Run the pipeline; rows land in Unity Catalog including the `sys_*` columns.
   Subsequent runs ingest only records whose `sys_updated_on` changed
   (incremental sync).

---

## Housekeeping

- **Rotate the admin password** after the POC (developer portal → Manage my
  instance → reset) — it was shared during setup — and update `.env`.
- `.env` contains credentials; it must stay untracked (gitignored).
- If the PDI is ever reclaimed: rerun steps 2, 3, 5 and recreate the
  Databricks connection (step 4) — with the API alternative in step 2 and the
  loader script, a full rebuild takes ~15 minutes.
