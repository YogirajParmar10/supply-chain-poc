from dataclasses import dataclass, field
from datetime import date, timedelta


def current_month_date_range(reference: date | None = None) -> tuple[date, date]:
    reference = reference or date.today()
    start = reference.replace(day=1)
    if reference.month == 12:
        next_month = date(reference.year + 1, 1, 1)
    else:
        next_month = date(reference.year, reference.month + 1, 1)
    end = next_month - timedelta(days=1)
    return start, end


@dataclass(frozen=True)
class PurchaseOrderSettings:
    count: int = 1_000
    start_date: date | None = None
    end_date: date | None = None
    min_lead_time_days: int = 3
    max_lead_time_days: int = 21
    status_weights: tuple[tuple[str, float], ...] = (
        ("DELIVERED", 0.70),
        ("CONFIRMED", 0.15),
        ("CREATED", 0.10),
        ("CANCELLED", 0.05),
    )

    @property
    def resolved_start_date(self) -> date:
        if self.start_date is not None:
            return self.start_date
        return current_month_date_range()[0]

    @property
    def resolved_end_date(self) -> date:
        if self.end_date is not None:
            return self.end_date
        return current_month_date_range()[1]


def default_purchase_order_settings() -> PurchaseOrderSettings:
    start, end = current_month_date_range()
    return PurchaseOrderSettings(start_date=start, end_date=end)


@dataclass(frozen=True)
class SalesOrderSettings:
    count: int = 1_000
    start_date: date | None = None
    end_date: date | None = None
    min_lead_time_days: int = 5
    max_lead_time_days: int = 30
    status_weights: tuple[tuple[str, float], ...] = (
        ("DELIVERED", 0.55),
        ("SHIPPED", 0.15),
        ("CONFIRMED", 0.15),
        ("CREATED", 0.10),
        ("CANCELLED", 0.05),
    )

    @property
    def resolved_start_date(self) -> date:
        if self.start_date is not None:
            return self.start_date
        return current_month_date_range()[0]

    @property
    def resolved_end_date(self) -> date:
        if self.end_date is not None:
            return self.end_date
        return current_month_date_range()[1]


def default_sales_order_settings() -> SalesOrderSettings:
    start, end = current_month_date_range()
    return SalesOrderSettings(start_date=start, end_date=end)


@dataclass(frozen=True)
class NoiseSettings:
    enabled: bool = True
    row_noise_rate: float = 0.06
    duplicate_rate: float = 0.01


@dataclass(frozen=True)
class DatasetSizes:
    raw_materials: int = 25
    finished_goods: int = 100
    suppliers: int = 10
    customers: int = 20
    plants: int = 2
    warehouses: int = 3


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    company_name: str = "FlexiPack Industries Ltd."
    sizes: DatasetSizes = DatasetSizes()
    purchase_orders: PurchaseOrderSettings = field(default_factory=default_purchase_order_settings)
    sales_orders: SalesOrderSettings = field(default_factory=default_sales_order_settings)
    noise: NoiseSettings = field(default_factory=NoiseSettings)
