"""Build forecast_serve gold tables from forecast_refined views."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from forecasting.config import ForecastConfig, DEFAULT_CONFIG
from forecasting.db import get_forecast_engine


def _exec(engine: Engine, sql: str, params: dict | None = None) -> None:
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


def build_sales_trend_monthly(engine: Engine) -> int:
    sql = """
    TRUNCATE forecast_serve.sales_trend_monthly;

    WITH bounds AS (
        SELECT
            date_trunc('month', MIN(order_date))::date AS min_month,
            date_trunc('month', MAX(order_date))::date AS max_month
        FROM forecast_refined.sales_orders
        WHERE status <> 'CANCELLED'
    ),
    months AS (
        SELECT generate_series(min_month, max_month, interval '1 month')::date AS month_start_date
        FROM bounds
        WHERE min_month IS NOT NULL AND max_month IS NOT NULL
    ),
    monthly AS (
        SELECT
            date_trunc('month', order_date)::date AS month_start_date,
            COUNT(*)::bigint AS order_count,
            COALESCE(SUM(quantity), 0)::bigint AS total_quantity
        FROM forecast_refined.sales_orders
        WHERE status <> 'CANCELLED'
        GROUP BY 1
    )
    INSERT INTO forecast_serve.sales_trend_monthly (
        month_start_date, year_month, order_count, total_quantity
    )
    SELECT
        m.month_start_date,
        to_char(m.month_start_date, 'YYYY-MM') AS year_month,
        COALESCE(t.order_count, 0),
        COALESCE(t.total_quantity, 0)
    FROM months m
    LEFT JOIN monthly t USING (month_start_date)
    ORDER BY m.month_start_date;
    """
    _exec(engine, sql)
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM forecast_serve.sales_trend_monthly")).scalar())


def build_top_selling_materials(engine: Engine, limit: int) -> int:
    sql = """
    TRUNCATE forecast_serve.top_selling_materials;

    INSERT INTO forecast_serve.top_selling_materials (
        sales_rank, material_id, material_name, material_type, sold_quantity
    )
    SELECT
        sales_rank,
        material_id,
        material_name,
        material_type,
        sold_quantity
    FROM (
        SELECT
            m.material_id,
            m.material_name,
            m.material_type,
            COALESCE(SUM(s.quantity), 0)::bigint AS sold_quantity,
            ROW_NUMBER() OVER (
                ORDER BY COALESCE(SUM(s.quantity), 0) DESC, m.material_id
            ) AS sales_rank
        FROM forecast_refined.materials m
        LEFT JOIN forecast_refined.sales_orders s
            ON s.material_id = m.material_id
           AND s.status <> 'CANCELLED'
        WHERE m.material_type = 'FINISHED_GOOD'
        GROUP BY m.material_id, m.material_name, m.material_type
    ) ranked
    WHERE sales_rank <= :limit
    ORDER BY sales_rank;
    """
    _exec(engine, sql, {"limit": limit})
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM forecast_serve.top_selling_materials")).scalar())


def build_material_summary(engine: Engine) -> int:
    sql = """
    TRUNCATE forecast_serve.material_summary;

    WITH purchased AS (
        SELECT material_id, SUM(quantity)::bigint AS purchased_quantity
        FROM forecast_refined.purchase_orders
        WHERE status <> 'CANCELLED'
        GROUP BY material_id
    ),
    sold AS (
        SELECT material_id, SUM(quantity)::bigint AS sold_quantity
        FROM forecast_refined.sales_orders
        WHERE status <> 'CANCELLED'
        GROUP BY material_id
    ),
    latest_inv AS (
        SELECT MAX(snapshot_date) AS max_date
        FROM forecast_refined.inventory
    ),
    current_inv AS (
        SELECT i.material_id, SUM(i.quantity)::bigint AS current_inventory
        FROM forecast_refined.inventory i
        CROSS JOIN latest_inv li
        WHERE i.snapshot_date = li.max_date
        GROUP BY i.material_id
    )
    INSERT INTO forecast_serve.material_summary (
        material_id, material_name, material_type,
        purchased_quantity, sold_quantity, current_inventory
    )
    SELECT
        m.material_id,
        m.material_name,
        m.material_type,
        COALESCE(p.purchased_quantity, 0),
        COALESCE(s.sold_quantity, 0),
        COALESCE(c.current_inventory, 0)
    FROM forecast_refined.materials m
    LEFT JOIN purchased p USING (material_id)
    LEFT JOIN sold s USING (material_id)
    LEFT JOIN current_inv c USING (material_id);
    """
    _exec(engine, sql)
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM forecast_serve.material_summary")).scalar())


def build_material_procurement_trend_monthly(engine: Engine) -> int:
    sql = """
    TRUNCATE forecast_serve.material_procurement_trend_monthly;

    WITH po_monthly AS (
        SELECT
            material_id,
            date_trunc('month', order_date)::date AS month_start_date,
            COUNT(*)::bigint AS purchase_order_count,
            SUM(quantity)::bigint AS purchase_quantity
        FROM forecast_refined.purchase_orders
        WHERE status <> 'CANCELLED'
        GROUP BY 1, 2
    ),
    so_monthly AS (
        SELECT
            material_id,
            date_trunc('month', order_date)::date AS month_start_date,
            COUNT(*)::bigint AS sales_order_count,
            SUM(quantity)::bigint AS sales_quantity
        FROM forecast_refined.sales_orders
        WHERE status <> 'CANCELLED'
        GROUP BY 1, 2
    ),
    production_with_month AS (
        SELECT
            po.input_material_id,
            po.output_material_id,
            po.input_quantity,
            po.output_quantity,
            date_trunc(
                'month',
                COALESCE(ord.end_date, ord.start_date)
            )::date AS month_start_date
        FROM forecast_refined.production_output po
        INNER JOIN forecast_refined.production_orders ord
            ON ord.production_order_id = po.production_order_id
        WHERE ord.status <> 'CANCELLED'
          AND COALESCE(ord.end_date, ord.start_date) IS NOT NULL
    ),
    input_monthly AS (
        SELECT
            input_material_id AS material_id,
            month_start_date,
            SUM(input_quantity)::bigint AS production_input_quantity
        FROM production_with_month
        GROUP BY 1, 2
    ),
    output_monthly AS (
        SELECT
            output_material_id AS material_id,
            month_start_date,
            SUM(output_quantity)::bigint AS production_output_quantity
        FROM production_with_month
        GROUP BY 1, 2
    ),
    material_months AS (
        SELECT material_id, month_start_date FROM po_monthly
        UNION
        SELECT material_id, month_start_date FROM so_monthly
        UNION
        SELECT material_id, month_start_date FROM input_monthly
        UNION
        SELECT material_id, month_start_date FROM output_monthly
    )
    INSERT INTO forecast_serve.material_procurement_trend_monthly (
        material_id, material_name, material_type, month_start_date, year_month,
        purchase_order_count, purchase_quantity,
        sales_order_count, sales_quantity,
        production_input_quantity, production_output_quantity
    )
    SELECT
        mm.material_id,
        m.material_name,
        m.material_type,
        mm.month_start_date,
        to_char(mm.month_start_date, 'YYYY-MM'),
        COALESCE(po.purchase_order_count, 0),
        COALESCE(po.purchase_quantity, 0),
        COALESCE(so.sales_order_count, 0),
        COALESCE(so.sales_quantity, 0),
        COALESCE(inp.production_input_quantity, 0),
        COALESCE(outp.production_output_quantity, 0)
    FROM material_months mm
    INNER JOIN forecast_refined.materials m USING (material_id)
    LEFT JOIN po_monthly po
        ON po.material_id = mm.material_id
       AND po.month_start_date = mm.month_start_date
    LEFT JOIN so_monthly so
        ON so.material_id = mm.material_id
       AND so.month_start_date = mm.month_start_date
    LEFT JOIN input_monthly inp
        ON inp.material_id = mm.material_id
       AND inp.month_start_date = mm.month_start_date
    LEFT JOIN output_monthly outp
        ON outp.material_id = mm.material_id
       AND outp.month_start_date = mm.month_start_date
    ORDER BY mm.material_id, mm.month_start_date;
    """
    _exec(engine, sql)
    with engine.connect() as conn:
        return int(
            conn.execute(
                text("SELECT COUNT(*) FROM forecast_serve.material_procurement_trend_monthly")
            ).scalar()
        )


def build_inventory_monthly(engine: Engine) -> int:
    """Month-end inventory on hand per material (sum across warehouses on last snapshot day)."""
    sql = """
    TRUNCATE forecast_serve.inventory_monthly;

    WITH daily AS (
        SELECT
            material_id,
            snapshot_date,
            date_trunc('month', snapshot_date)::date AS month_start_date,
            SUM(quantity)::bigint AS quantity
        FROM forecast_refined.inventory
        GROUP BY material_id, snapshot_date, date_trunc('month', snapshot_date)
    ),
    month_end_dates AS (
        SELECT
            material_id,
            month_start_date,
            MAX(snapshot_date) AS snapshot_date
        FROM daily
        GROUP BY material_id, month_start_date
    )
    INSERT INTO forecast_serve.inventory_monthly (
        material_id, month_start_date, year_month, inventory_on_hand
    )
    SELECT
        d.material_id,
        d.month_start_date,
        to_char(d.month_start_date, 'YYYY-MM'),
        d.quantity
    FROM daily d
    INNER JOIN month_end_dates m
        ON m.material_id = d.material_id
       AND m.month_start_date = d.month_start_date
       AND m.snapshot_date = d.snapshot_date
    ORDER BY d.material_id, d.month_start_date;
    """
    _exec(engine, sql)
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM forecast_serve.inventory_monthly")).scalar())


def build_machine_downtime_monthly(engine: Engine) -> int:
    sql = """
    TRUNCATE forecast_serve.machine_downtime_monthly;

    INSERT INTO forecast_serve.machine_downtime_monthly (
        plant_id, month_start_date, year_month, downtime_event_count, downtime_hours
    )
    SELECT
        plant_id,
        date_trunc('month', start_time)::date AS month_start_date,
        to_char(date_trunc('month', start_time), 'YYYY-MM') AS year_month,
        COUNT(*)::bigint AS downtime_event_count,
        SUM(EXTRACT(EPOCH FROM (end_time - start_time)) / 3600.0) AS downtime_hours
    FROM forecast_refined.machine_downtime
    WHERE end_time > start_time
    GROUP BY 1, 2, 3
    ORDER BY 1, 2;
    """
    _exec(engine, sql)
    with engine.connect() as conn:
        return int(
            conn.execute(text("SELECT COUNT(*) FROM forecast_serve.machine_downtime_monthly")).scalar()
        )


def build_forecast_features_monthly(engine: Engine) -> int:
    """
    Dense month spine for top finished goods with procurement + inventory + downtime.

    Downtime is plant-level; we allocate total plant downtime hours equally across
    top materials as a shared capacity exogenous signal.
    """
    sql = """
    TRUNCATE forecast_serve.forecast_features_monthly;

    WITH top_mats AS (
        SELECT material_id, material_name
        FROM forecast_serve.top_selling_materials
    ),
    bounds AS (
        SELECT
            date_trunc('month', MIN(month_start_date))::date AS min_month,
            date_trunc('month', MAX(month_start_date))::date AS max_month
        FROM forecast_serve.material_procurement_trend_monthly
    ),
    months AS (
        SELECT generate_series(min_month, max_month, interval '1 month')::date AS month_start_date
        FROM bounds
        WHERE min_month IS NOT NULL AND max_month IS NOT NULL
    ),
    spine AS (
        SELECT t.material_id, t.material_name, m.month_start_date
        FROM top_mats t
        CROSS JOIN months m
    ),
    downtime_total AS (
        SELECT
            month_start_date,
            SUM(downtime_hours) AS downtime_hours
        FROM forecast_serve.machine_downtime_monthly
        GROUP BY month_start_date
    ),
    top_count AS (
        SELECT GREATEST(COUNT(*), 1)::float AS n FROM top_mats
    )
    INSERT INTO forecast_serve.forecast_features_monthly (
        material_id, material_name, month_start_date, year_month,
        sales_order_count, sales_quantity,
        purchase_order_count, purchase_quantity,
        production_input_quantity, production_output_quantity,
        inventory_on_hand, downtime_hours
    )
    SELECT
        s.material_id,
        s.material_name,
        s.month_start_date,
        to_char(s.month_start_date, 'YYYY-MM'),
        COALESCE(p.sales_order_count, 0),
        COALESCE(p.sales_quantity, 0),
        COALESCE(p.purchase_order_count, 0),
        COALESCE(p.purchase_quantity, 0),
        COALESCE(p.production_input_quantity, 0),
        COALESCE(p.production_output_quantity, 0),
        COALESCE(i.inventory_on_hand, 0),
        COALESCE(d.downtime_hours, 0) / tc.n AS downtime_hours
    FROM spine s
    CROSS JOIN top_count tc
    LEFT JOIN forecast_serve.material_procurement_trend_monthly p
        ON p.material_id = s.material_id
       AND p.month_start_date = s.month_start_date
    LEFT JOIN forecast_serve.inventory_monthly i
        ON i.material_id = s.material_id
       AND i.month_start_date = s.month_start_date
    LEFT JOIN downtime_total d
        ON d.month_start_date = s.month_start_date
    ORDER BY s.material_id, s.month_start_date;
    """
    _exec(engine, sql)
    with engine.connect() as conn:
        return int(
            conn.execute(text("SELECT COUNT(*) FROM forecast_serve.forecast_features_monthly")).scalar()
        )


def build_company_forecast_features_monthly(engine: Engine) -> int:
    sql = """
    TRUNCATE forecast_serve.company_forecast_features_monthly;

    WITH sales AS (
        SELECT
            month_start_date,
            order_count AS sales_order_count,
            total_quantity AS sales_quantity
        FROM forecast_serve.sales_trend_monthly
    ),
    purchase AS (
        SELECT
            month_start_date,
            SUM(purchase_quantity)::bigint AS purchase_quantity
        FROM forecast_serve.material_procurement_trend_monthly
        GROUP BY month_start_date
    ),
    production AS (
        SELECT
            month_start_date,
            SUM(production_output_quantity)::bigint AS production_output_quantity
        FROM forecast_serve.material_procurement_trend_monthly
        WHERE material_type = 'FINISHED_GOOD'
        GROUP BY month_start_date
    ),
    inventory AS (
        SELECT
            month_start_date,
            SUM(inventory_on_hand)::bigint AS inventory_on_hand
        FROM forecast_serve.inventory_monthly
        GROUP BY month_start_date
    ),
    downtime AS (
        SELECT
            month_start_date,
            SUM(downtime_hours) AS downtime_hours
        FROM forecast_serve.machine_downtime_monthly
        GROUP BY month_start_date
    )
    INSERT INTO forecast_serve.company_forecast_features_monthly (
        month_start_date, year_month,
        sales_order_count, sales_quantity,
        purchase_quantity, production_output_quantity,
        inventory_on_hand, downtime_hours
    )
    SELECT
        s.month_start_date,
        to_char(s.month_start_date, 'YYYY-MM'),
        s.sales_order_count,
        s.sales_quantity,
        COALESCE(p.purchase_quantity, 0),
        COALESCE(pr.production_output_quantity, 0),
        COALESCE(i.inventory_on_hand, 0),
        COALESCE(d.downtime_hours, 0)
    FROM sales s
    LEFT JOIN purchase p USING (month_start_date)
    LEFT JOIN production pr USING (month_start_date)
    LEFT JOIN inventory i USING (month_start_date)
    LEFT JOIN downtime d USING (month_start_date)
    ORDER BY s.month_start_date;
    """
    _exec(engine, sql)
    with engine.connect() as conn:
        return int(
            conn.execute(
                text("SELECT COUNT(*) FROM forecast_serve.company_forecast_features_monthly")
            ).scalar()
        )


def build_all_features(
    engine: Engine | None = None,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> dict[str, int]:
    engine = engine or get_forecast_engine()
    counts = {
        "sales_trend_monthly": build_sales_trend_monthly(engine),
        "top_selling_materials": build_top_selling_materials(engine, config.top_materials_limit),
        "material_summary": build_material_summary(engine),
        "material_procurement_trend_monthly": build_material_procurement_trend_monthly(engine),
        "inventory_monthly": build_inventory_monthly(engine),
        "machine_downtime_monthly": build_machine_downtime_monthly(engine),
        "forecast_features_monthly": build_forecast_features_monthly(engine),
        "company_forecast_features_monthly": build_company_forecast_features_monthly(engine),
    }
    return counts
