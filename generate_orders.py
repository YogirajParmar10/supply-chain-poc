"""Generate purchase and sales orders for a configured date range."""

import calendar
from datetime import date

from generator.config.settings import (
    GeneratorConfig,
    PurchaseOrderSettings,
    SalesOrderSettings,
)
from generator.main import generate_purchase_order_data, generate_sales_order_data

YEAR = 2025
MONTH = 2


def month_date_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    return start, end


def main() -> None:
    start_date, end_date = month_date_range(YEAR, MONTH)

    config = GeneratorConfig(
        purchase_orders=PurchaseOrderSettings(
            start_date=start_date,
            end_date=end_date,
        ),
        sales_orders=SalesOrderSettings(
            start_date=start_date,
            end_date=end_date,
        ),
    )

    purchase_order_rows = generate_purchase_order_data(config)
    sales_order_rows = generate_sales_order_data(config)

    print(f"Generated orders for {start_date} to {end_date}")
    print(f"  - purchase_orders: {purchase_order_rows} rows")
    print(f"  - sales_orders: {sales_order_rows} rows")


if __name__ == "__main__":
    main()
