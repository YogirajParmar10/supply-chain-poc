# Local Sales Forecasting

Postgres-native forecasting package that mirrors Databricks gold tables locally, then trains **Prophet** models with exogenous signals (procurement, inventory, machine downtime).

## Schemas

| Schema | Purpose |
|--------|---------|
| `forecast_refined` | Typed views over `public` bronze tables |
| `forecast_serve` | Gold feature tables (month spines, top SKUs, model matrix) |
| `forecast_ml` | Run metadata, backtests, 12-month forecasts |

Bronze data in `public` is never modified except optional `machine_downtime` generation.

## Quick start

```bash
# from repo root, with .venv active and DATABASE_URL pointing at erp_demo
pip install -r requirements.txt

python -m forecasting.pipelines.run_all
```

Useful flags:

```bash
python -m forecasting.pipelines.run_all --force-downtime   # regenerate downtime history
python -m forecasting.pipelines.run_all --skip-train       # gold tables only
python -m forecasting.pipelines.run_all --top-materials 15
```

## What it builds

1. Generates multi-year `public.machine_downtime` (if missing)
2. Applies `forecasting/sql/*.sql`
3. Builds serve tables:
   - `sales_trend_monthly`
   - `top_selling_materials`
   - `material_summary`
   - `material_procurement_trend_monthly`
   - `inventory_monthly`
   - `machine_downtime_monthly`
   - `forecast_features_monthly` (top finished goods)
   - `company_forecast_features_monthly`
4. Trains Prophet (no naive baselines) at:
   - **company** grain → `sales_quantity`
   - **material** grain → top N finished goods `sales_quantity`
5. Writes results to `forecast_ml.*`

## Exogenous regressors

| Feature | Source |
|---------|--------|
| `purchase_quantity` | PO monthly totals |
| `production_output_quantity` | MES production output |
| `inventory_on_hand` | Month-end WMS inventory |
| `downtime_hours` | Aggregated machine downtime |

Future-month regressors are filled with same-month-last-year values (else trailing 3-month mean).

Company models use multiplicative yearly seasonality. Material models use **additive** seasonality (more stable when some months are near-zero). Prefer **wMAPE** over MAPE for SKU backtests.

## Inspect outputs

```sql
-- latest company forecast
SELECT year_month, ROUND(yhat) AS forecast, ROUND(yhat_lower) AS lo, ROUND(yhat_upper) AS hi
FROM forecast_ml.sales_forecast_monthly
WHERE grain = 'company'
ORDER BY run_id DESC, forecast_month
LIMIT 12;

-- backtest quality
SELECT grain_id, metric_name, ROUND(metric_value::numeric, 2) AS value
FROM forecast_ml.forecast_backtest
WHERE run_id = (SELECT MAX(run_id) FROM forecast_ml.forecast_runs WHERE grain = 'material')
ORDER BY grain_id, metric_name;
```

## Layout

```text
forecasting/
├── config.py
├── db.py
├── sql/                 # schema + DDL
├── features/            # downtime gen + gold builders
├── models/              # Prophet train / infer
├── pipelines/           # CLI entrypoint
└── notebooks/           # optional exploration
```
