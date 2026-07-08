from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

import numpy as np

from generator.config.settings import (
    GeneratorConfig,
    HistoryBackfillSettings,
    ProductionOrderSettings,
    PurchaseOrderSettings,
    SalesOrderSettings,
)


@dataclass(frozen=True)
class HistoryMonth:
    year: int
    month: int
    start_date: date
    end_date: date
    purchase_order_count: int
    sales_order_count: int
    production_order_count: int


def month_date_range(year: int, month: int, *, cap_end: date | None = None) -> tuple[date, date]:
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    if cap_end is not None and end > cap_end:
        end = cap_end
    return start, end


def iter_history_months(settings: HistoryBackfillSettings) -> list[HistoryMonth]:
    months: list[HistoryMonth] = []
    year = settings.start_month.year
    month = settings.start_month.month
    rng = np.random.default_rng(settings.volume_seed)

    for _ in range(settings.month_count):
        start_date, end_date = month_date_range(year, month, cap_end=settings.cap_end_date)
        if start_date > end_date:
            break

        seasonality = settings.seasonality.get(month, 1.0)
        purchase_count = int(
            round(rng.integers(settings.purchase_orders_min, settings.purchase_orders_max + 1) * seasonality)
        )
        sales_count = int(
            round(rng.integers(settings.sales_orders_min, settings.sales_orders_max + 1) * seasonality)
        )
        production_count = max(
            settings.production_orders_min,
            int(round(sales_count * settings.production_orders_ratio)),
        )
        production_count = min(production_count, settings.production_orders_max)

        months.append(
            HistoryMonth(
                year=year,
                month=month,
                start_date=start_date,
                end_date=end_date,
                purchase_order_count=purchase_count,
                sales_order_count=sales_count,
                production_order_count=production_count,
            )
        )

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return months


def generate_history_month(
    history_month: HistoryMonth,
    config: GeneratorConfig,
) -> GeneratorConfig:
    """Return a GeneratorConfig scoped to one calendar month."""
    purchase_orders = PurchaseOrderSettings(
        count=history_month.purchase_order_count,
        start_date=history_month.start_date,
        end_date=history_month.end_date,
        min_lead_time_days=config.purchase_orders.min_lead_time_days,
        max_lead_time_days=config.purchase_orders.max_lead_time_days,
        status_weights=config.purchase_orders.status_weights,
    )
    sales_orders = SalesOrderSettings(
        count=history_month.sales_order_count,
        start_date=history_month.start_date,
        end_date=history_month.end_date,
        min_lead_time_days=config.sales_orders.min_lead_time_days,
        max_lead_time_days=config.sales_orders.max_lead_time_days,
        status_weights=config.sales_orders.status_weights,
    )
    production_orders = ProductionOrderSettings(
        count=history_month.production_order_count,
        start_date=history_month.start_date,
        end_date=history_month.end_date,
        min_duration_days=config.production_orders.min_duration_days,
        max_duration_days=config.production_orders.max_duration_days,
        status_weights=config.production_orders.status_weights,
    )

    return GeneratorConfig(
        seed=config.seed,
        company_name=config.company_name,
        sizes=config.sizes,
        purchase_orders=purchase_orders,
        sales_orders=sales_orders,
        production_orders=production_orders,
        noise=config.noise,
        wms=config.wms,
        history=config.history,
    )
