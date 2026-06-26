from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class PurchaseOrderSettings:
    count: int = 2_000
    start_date: date = date(2025, 1, 1)
    end_date: date = date(2025, 12, 31)
    min_lead_time_days: int = 3
    max_lead_time_days: int = 21
    status_weights: tuple[tuple[str, float], ...] = (
        ("DELIVERED", 0.70),
        ("CONFIRMED", 0.15),
        ("CREATED", 0.10),
        ("CANCELLED", 0.05),
    )


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
    purchase_orders: PurchaseOrderSettings = field(default_factory=PurchaseOrderSettings)
    output_dir: Path = Path("output")

    @property
    def erp_output_dir(self) -> Path:
        return self.output_dir / "erp"
